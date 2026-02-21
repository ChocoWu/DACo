import math
import re
import os
import json
from prompts.prompts import *
from utils.tool import visualize_vp_on_bev


class PromptManagerBase(object):
    def __init__(self, args):
        self.args = args
        
    def get_prompts(self, *args, **kwargs):
        raise NotImplementedError
    
    def parse_action(self, *args, **kwargs):
        raise NotImplementedError
    
    def update_history(self, *args, **kwargs):
        raise NotImplementedError
    

class PromptManager2D(PromptManagerBase):
    def __init__(self, args):
        super().__init__(args)
        self.history = []   # [(vpid, action_option)]
        self.graph = {}     # {vpid: candidate's vpid list}
        self.vp2idx = {}    # assign ids to viewpoints
        self.vp2img = {}
        self.plans = ["Navigation has just started, with no planning yet."]

    def get_direction_action(self, rel_heading, rel_elevation):
        action_text = ""
        if rel_elevation > 0:
            action_text = 'go up'
        elif rel_elevation < 0:
            action_text = 'go down'
        else:
            if rel_heading < 0:
                if rel_heading >= -math.pi / 2:
                    action_text = 'turn left'
                elif rel_heading < -math.pi / 2 and rel_heading > -math.pi * 3 / 2:
                    action_text = 'turn around'
                else:
                    action_text = 'turn right'
            elif rel_heading > 0:
                if rel_heading <= math.pi / 2:
                    action_text = 'turn right'
                elif rel_heading > math.pi / 2 and rel_heading < math.pi * 3 / 2:
                    action_text = 'turn around'
                else:
                    action_text = 'turn left'
            elif rel_heading == 0:
                action_text = 'go forward'
        return action_text
    
    def get_action_options(self, ob):
        previous_angle = {'heading': ob['heading'], 'elevation': ob['elevation']}
        action_options_text = ""
        action_options = []
        used_idx_list = []   
        cand_vpids = []

        for i, candidate in enumerate(ob['candidate']):
            cand_vpids.append(candidate['viewpointId'])
            if candidate['viewpointId'] not in self.vp2idx.keys():      # register new viewpoint
                map_size = len(self.vp2idx)
                self.vp2idx[candidate['viewpointId']] = map_size
                self.vp2img[candidate['viewpointId']] = candidate['image']

            direction = self.get_direction_action(candidate['absolute_heading'] - previous_angle['heading'], candidate['absolute_elevation'] - 0)

            action_option = chr(i + 65) + '. ' + direction + f" to Place {self.vp2idx[candidate['viewpointId']]} which is corresponding to Image {self.vp2idx[candidate['viewpointId']]}"
            used_idx_list.append(self.vp2idx[candidate['viewpointId']])
            # print(f"candidate viewpoint: {candidate['viewpointId']}, id: {self.vp2idx[candidate['viewpointId']]}, image: {candidate['image']}")
            action_options_text += "\n\t" + action_option
            action_options.append(action_option)
        action_options_text += "\n\t" + chr(len(ob['candidate']) + 65) + ". Stop"
        action_options_text += "\n\t" + chr(len(ob['candidate']) + 66) + ". Replan needed"
        
        # update graph
        if ob['viewpoint'] not in self.graph.keys():
            self.graph[ob['viewpoint']] = set(cand_vpids)

        return action_options_text, action_options, used_idx_list
    
    def init_map(self, init_ob):
        init_vp = init_ob['viewpoint']
        self.vp2idx[init_vp] = 0
        self.vp2img[init_vp] = None


    def get_map_prompt(self):   
        graph_text = ''
        for vp, neighbors in self.graph.items():
            adj_text = ''
            for adj_vp in neighbors:
                adj_idx = self.vp2idx[adj_vp]
                adj_text += f""" {adj_idx},"""
    
            graph_text += f"""\n\tPlace {self.vp2idx[vp]} is connected with Places{adj_text}"""[:-1]

        return graph_text
    
    def get_history_prompt(self):
        if len(self.history) == 0:
            return "The navigation has just begun, with no history.", []
        
        used_idx_list = []
        history_text = ''
        for i, (vp, action_option) in enumerate(self.history):
            history_text += f"\n\tstep {i}: {action_option[3:]}"
            used_idx_list.append(self.vp2idx[vp])

        return history_text, used_idx_list
    
    def get_prompts(self, plan, ob, step):
        sys_prompt = SYS_PROMPT_2D

        action_options_text, action_options, used_idx_list_act = self.get_action_options(ob)
        graph_text = self.get_map_prompt()
        history_text, used_idx_list_his = self.get_history_prompt()

        user_prompt_text = USER_PROMPT_2D.format(
            instruction=ob['instruction'],
            global_plan=plan,
            history_text=history_text,
            graph_text=graph_text,
            step=str(step),
            action_options=action_options_text
        )

        # find used images, create map of id-image
        user_prompt_img = {}    
        idx2vp = {v: k for k, v in self.vp2idx.items()}
        used_idx_list = sorted(set(used_idx_list_his + used_idx_list_act)) # type: ignore     
        for idx in used_idx_list:
            vp = idx2vp[idx]
            user_prompt_img[idx] = self.vp2img[vp]

        return sys_prompt, user_prompt_text, user_prompt_img, action_options

    def parse_action(self, nav_output, ob):
        output = nav_output.strip()

        pattern = re.compile("Action")  # keyword
        matches = pattern.finditer(output)
        indices = [match.start() for match in matches]
        if len(indices) == 0:
            return -1
        output = output[indices[-1]:]

        search_result = re.findall(r"Action:\s*([A-Z])", output)
        if search_result:
            output = search_result[-1]
            output_idx = ord(output) - ord('A')
            if output_idx == len(ob['candidate']):   # stop
                output_idx = -1
            elif output_idx > len(ob['candidate']):     # replan
                output_idx = -2
        else:
            output_idx = -1
        return output_idx

    def update_history(self, vp, action_option):
        self.history.append((vp, action_option))
        return 



class PromptManager3D(PromptManagerBase):
    def __init__(self, args):
        super().__init__(args)
        self.plans = []

    def get_prompts(self, ob, cur_loc, traj, step, target):
        is_first = target is None
        if is_first:
            if self.args.dataset != 'reverie':
                sys_prompt = SYS_PROMPT_3D 
            else:
                sys_prompt = SYS_PROMPT_3D_REVERIE
        else:
            sys_prompt = SYS_PROMPT_3D_FOR_REPLAN
        instr = ob['instruction'] if is_first else target

        if is_first:
            user_prompt_text = USER_PROMPT_3D.format(
                instruction=instr,
                cur_loc=cur_loc,
                prev_plan="The navigation has just started, no previous plan" if len(self.plans) == 0 else self.plans[-1]
            )
        else:
            user_prompt_text = USER_PROMPT_3D_FOR_REPLAN.format(
                instruction=instr,
                cur_loc=cur_loc
            )
        user_prompt_img = {}   

        output_dir = os.path.join(self.args.traj_img_dir, ob['instr_id'])
        if is_first:
            visualize_vp_on_bev(bev_img_dir=self.args.bev_dir, output_dir=output_dir, scan_id=ob['scan'], vps=traj, step=step)

        for img in os.listdir(os.path.join(self.args.bev_dir, ob['scan'])):
            floor = img.split('.')[0]   # e.g. floor1, floor2
            user_prompt_img[floor] = os.path.join(self.args.bev_dir, ob['scan'], img)
        
        for img in os.listdir(os.path.join(self.args.traj_img_dir, ob['instr_id'])):
            if f"step{step}" in img:     
                floor = img.split("_")[0]
                user_prompt_img[floor] = os.path.join(self.args.traj_img_dir, ob['instr_id'], img)
    
        return sys_prompt, user_prompt_text, user_prompt_img
    
    def parse_action(self, llm_output):
        try:
            data = json.loads(llm_output.strip())
            
            if "New Plan" not in data:
                return {
                    "success": False,
                    "error": "Missing 'Plan' field in the response."
                }
            
            thought = data['Thought']
            plan = data["New Plan"]
            
            self.plans.append(plan)

            return {
                "success": True,
                "data": plan,
                "thought": thought,
            }
    
        except json.JSONDecodeError as e:
            print(llm_output, "!!!!!!!!!!!!!!!!")
            return {
                "success": False,
                "data": llm_output,
                "error": f"Invalid JSON format. Parsing failed: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "data": llm_output,
                "error": f"Unexpected error during parsing: {str(e)}"
            }
        
    def get_cur_loc_prompt(self, ob):
        sys_prompt = SYS_PROMPT_FOR_CUR_LOC
        user_prompt_text = USER_PROMPT_FOR_CUR_LOC

        front_id = ob["viewIndex"]

        # only choose images with elevation angle = 0
        if front_id < 12:
            front_id += 12
        elif front_id > 23:
            front_id -= 12
        right_ids = [(front_id + i) % 24 for i in range(1, 5)] 
        left_ids = [(front_id - i) % 12 + 12 for i in range(1, 5)]
        user_prompt_img = {}
        user_prompt_img[f'Scene {front_id} (in front of you)'] = os.path.join(self.args.img_root, ob['scan'], ob['viewpoint'], str(ob['viewIndex']) + '.jpg') 
        for img in os.listdir(os.path.join(self.args.img_root, ob['scan'], ob['viewpoint'])):
            if str(ob['viewIndex']) in img:
                continue
            img_index = int(img.split(".")[0])
            if img_index < 12 or img_index > 23:    
                continue
            elif img_index in right_ids:
                user_prompt_img[f'Scene {img_index} (on your right)'] = os.path.join(self.args.img_root, ob['scan'], ob['viewpoint'], img)
            elif img_index in left_ids:
                user_prompt_img[f'Scene {img_index} (on your left)'] = os.path.join(self.args.img_root, ob['scan'], ob['viewpoint'], img)
            else: 
                user_prompt_img[f'Scene {img_index} (behind of you)'] = os.path.join(self.args.img_root, ob['scan'], ob['viewpoint'], img)
        return sys_prompt, user_prompt_text, user_prompt_img
    
    def get_tar_loc_prompts(self, ob):
        sys_prompt = SYS_PROMPT_3D_FOR_TAR_LOC
        user_prompt_text = USER_PROMPT_3D_FOR_TAR_LOC.format(
            instruction=ob['instruction']
        )
        return sys_prompt, user_prompt_text, {}
