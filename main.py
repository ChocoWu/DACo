import os
import json
import time
from utils.data import set_random_seed, construct_instrs
from my_parser import parse_args
from agents.action_generator import ActionGenerator
from agents.global_planner import GlobalPlanner
from env import R2RNavBatch
from utils.eval import print_metric


def build_dataset(args, is_test=True):
    dataset_class = R2RNavBatch
    split = args.split

    if 'processed' in split:        
        with open(os.path.join(args.anno_dir, split+'.json'), 'r') as f:
            val_instr_data = json.load(f)


        if args.end is None:
            args.end = len(val_instr_data)
        
        # all data
        val_instr_data = val_instr_data[args.start:args.end]
        


        print(f'------------------ Evaluate {args.start}-{args.end} in {split} ------------------')

    else:
        val_instr_data = construct_instrs(
            args.anno_dir, args.dataset, split,
            max_instr_len=args.max_instr_len,
            is_test=is_test
        )

    val_env = dataset_class(
        val_instr_data, args.connectivity_dir, batch_size=args.batch_size,
        seed=args.seed,
        name=split, 
        args=args,
    )   # evaluation using all objects

    return val_env


def valid(args, val_env):
    print(f"Start evaluating {val_env.name}")
    print('running...')

    
    for i, instr in enumerate(val_env.data):
        print(f'================== {i+1} / {len(val_env.data)}, instruction id: {instr["instr_id"]} ==================')
        global_planner = GlobalPlanner(args=args)
        action_generator = ActionGenerator(env=val_env, args=args, partner=global_planner)

        traj = action_generator.test()
        pred = {'instr_id': instr['instr_id'], 'trajectory': traj['path'], 'a_t': traj['actions']}
       
        with open(os.path.join(args.pred_dir, str(i + 1) + '_' + instr['instr_id'] + '.json'), 'w') as f:
            json.dump(pred, f, ensure_ascii=False)
            print(f"record file to {os.path.join(args.pred_dir, str(i + 1) + '_' + instr['instr_id'] + '.json')}")

    print('================== Evaluation is finished! ==================')
        
        

def main():
    args = parse_args()
    set_random_seed(args.seed)
    val_env = build_dataset(args)
    start_time = time.time()
    valid(args, val_env)
    print_metric(args, val_env, start_time)


if __name__ == '__main__':
    main()