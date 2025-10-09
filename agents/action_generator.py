from api.api import call_2D_llm
from prompts.prompt_manager import PromptManager2D
from agents.global_planner import GlobalPlanner

class ActionGenerator(object):
    env_actions = {
        'left': (0, -1, 0),  # left
        'right': (0, 1, 0),  # right
        'up': (0, 0, 1),  # up
        'down': (0, 0, -1),  # down
        'forward': (1, 0, 0),  # forward
        '<end>': (0, 0, 0),  # <end>
        '<start>': (0, 0, 0),  # <start>
        '<ignore>': (0, 0, 0)  # <ignore>
    }
    for k, v in env_actions.items():
        env_actions[k] = [[vx] for vx in v] # type: ignore

    def __init__(self, env, args, partner: GlobalPlanner):
        self.env = env
        self.results = {}       
        self.args = args
        self.prompt_manager = PromptManager2D(args)
        self.partner = partner
    
    def reset_history_map(self):
        self.prompt_manager.history = []
        self.prompt_manager.graph = {}
    
    def extract_history(self, user_prompt_img):
        history_text, used_img_ids = self.prompt_manager.get_history_prompt()
        history_img = {}
        for id in used_img_ids:
            history_img[id] = user_prompt_img[int(id)]
        return {'text': history_text, 'img': history_img}
        
    def make_equiv_action(self, action, ob, traj):
        def take_action(name):
            if type(name) is int:       # Go to the next viewpoint
                self.env.env.sim.makeAction([name], [0], [0])
            else:                       # Adjust
                self.env.env.sim.makeAction(*self.env_actions[name])

        if action != -1:            # -1 means stop
            select_candidate = ob['candidate'][action]
            src_point = ob['viewIndex']
            trg_point = select_candidate['pointId']
            src_level = (src_point) // 12  # The point idx started from 0
            trg_level = (trg_point) // 12
            while src_level < trg_level:    # Tune up
                take_action('up')
                src_level += 1
            while src_level > trg_level:    # Tune down
                take_action('down')
                src_level -= 1
            while self.env.env.sim.getState()[0].viewIndex != trg_point:    # Turn right until the target
                take_action('right')
            assert select_candidate['viewpointId'] == \
                    self.env.env.sim.getState()[0].navigableLocations[select_candidate['idx']].viewpointId
            take_action(select_candidate['idx']) # j+1: idx for navigable location

            state = self.env.env.sim.getState()[0]
            if traj is not None:
                traj['path'].append([state.location.viewpointId])
        return 

    def navigation(self, init_ob):

        ob = init_ob
        
        # Record the navigation path
        traj = {
            'path': [[ob['viewpoint']]],        # every item is a list, not bug
            'actions': []
        }

        user_prompt_text = ''
        user_prompt_img = {}
        
        target = self.partner.get_target(ob)

        replan_cnt = 0
        for step in range(self.args.max_action_len):
            
            # dynamic plan
            plan = self.partner.global_plan(ob, traj['path'], step)

            print('-------- Current Plan --------')
            print(plan)
        

            sys_prompt, user_prompt_text, user_prompt_img, action_options = self.prompt_manager.get_prompts(plan, ob, step)
                
            print('-------- Local Action Prompts --------')
            print(user_prompt_text)
            # print(user_prompt_img)
    
            nav_output = call_2D_llm(sys_prompt, user_prompt_text, user_prompt_img, model=self.args.llm)
            
            print('-------- Local Output --------')
            print(nav_output)

            ''' parse action '''
            action = self.prompt_manager.parse_action(nav_output=nav_output, ob=ob) 
            
            while action == -2 and replan_cnt < self.args.max_re_plan:        # replan
                replan_cnt += 1
                plan = self.partner.global_plan(ob, traj['path'], step, target)
                sys_prompt, user_prompt_text, user_prompt_img, action_options = self.prompt_manager.get_prompts(plan, ob, step)
                print('-------- Local Replan Action Prompts --------')
                print(user_prompt_text)
                nav_output = call_2D_llm(sys_prompt, user_prompt_text, user_prompt_img, model=self.args.llm)
                print('-------- Local Replan Output --------')
                print(nav_output)
                action = self.prompt_manager.parse_action(nav_output=nav_output, ob=ob)     
            if action < -1:
                action = -1

            traj['actions'].append(action)


            ''' interact with simulator '''
            self.make_equiv_action(action, ob, traj)

            
            ''' single navigation is end, update history '''
            self.prompt_manager.update_history(vp=ob['candidate'][action]['viewpointId'], action_option=action_options[action]) 
            if action != -1:
                ob = self.env._get_obs()[0]    
            else:
                return {'status': 'success', 'traj': traj}     
            
        return {'status': 'fail', 'traj': traj}  

    def test(self):
        ### initialize the environment
        init_ob = self.env.reset()[0]        # return the batch observation, we only support batch_size = 1

        # initialize two dicts: vp2idx, vp2img
        self.prompt_manager.init_map(init_ob)

        message_2D = self.navigation(init_ob=init_ob)

        return message_2D['traj']



        
    