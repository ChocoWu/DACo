import json
from prompts.prompt_manager import PromptManager3D
from api.api import call_2D_llm


class GlobalPlanner(object):
    def __init__(self, args):
        self.args = args
        self.prompt_manager = PromptManager3D(args)
        self.history = []
        self.goal_desc = ""
        
        
    def get_cur_loc_desc(self, ob):
        sys_prompt, user_prompt_text, user_prompt_img = self.prompt_manager.get_cur_loc_prompt(ob)
        return call_2D_llm(system=sys_prompt, prompt=user_prompt_text, image_dict=user_prompt_img, model=self.args.llm)

    def global_plan(self, ob, traj, step, target=None):
        cur_loc = self.get_cur_loc_desc(ob)

        sys_prompt, user_prompt_text, user_prompt_img = self.prompt_manager.get_prompts(ob, cur_loc, traj, step, target)

        print('-------- Current Location Desc --------')
        print(cur_loc)
        

        # print('-------- Global Prompt --------')
        # print(user_prompt_text)

        global_plan_output = call_2D_llm(sys_prompt, user_prompt_text, user_prompt_img, model=self.args.llm)
        message = self.prompt_manager.parse_action(global_plan_output)
        plan = message['data']
        if not message['success']:
            print(message['error'], ",  Now try again!")
        
        # print('-------- Global Output --------')
        # print(plan)
        # print('-------- Global Destination Description --------')
        # print(self.goal_desc)
        return plan
    
    def get_target(self, ob):
        sys_prompt, user_prompt_text, user_prompt_img = self.prompt_manager.get_tar_loc_prompts(ob)
        tar_loc = call_2D_llm(system=sys_prompt, prompt=user_prompt_text, image_dict=user_prompt_img, model=self.args.llm)
        # print(tar_loc)
        tar_loc = json.loads(tar_loc)['Answer']
        return tar_loc
