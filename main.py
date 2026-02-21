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

        val_instr_data = [data for data in val_instr_data if data['instr_id'] == '1774_0']
        

        print(f'------------------ Evaluate {args.start}-{args.end - 1} in {split} ------------------')

    else:
        val_instr_data = construct_instrs(
            args.anno_dir, args.dataset, split,
            max_instr_len=args.max_instr_len,
            is_test=is_test
        )
    
    # ------------------ Resume from Breakpoint & Log Cleanup ------------------
    if args.pred_dir and os.path.exists(args.pred_dir):
        finished_ids = set()
        # get finished task ids
        for fname in os.listdir(args.pred_dir):
            if fname.endswith('.json'):
                # parse filename: 1_6250_2.json -> 6250_2
                try:
                    parts = fname.split('_', 1)
                    if len(parts) == 2:
                        instr_id = parts[1].replace('.json', '')
                        finished_ids.add(instr_id)
                except Exception:
                    continue
        
        total_before = len(val_instr_data)
        
        # Filter: Keep only tasks whose instr_id is NOT in finished_ids
        val_instr_data = [
            item for item in val_instr_data 
            if item['instr_id'] not in finished_ids
        ]
        
        print(f"Dataset Filtered: Ignored {total_before - len(val_instr_data)} completed tasks.")
        print(f"Remaining tasks to run: {len(val_instr_data)}")

        # Cleanup: Remove old API usage logs for remaining tasks to avoid appended duplicates
        if args.log_dir and os.path.exists(args.log_dir):
            removed_count = 0
            for item in val_instr_data:
                current_id = str(item['instr_id'])
                # File naming convention: 'api_usage_log_{instr_id}.jsonl'
                log_filename = f"api_usage_log_{current_id}.jsonl" 
                log_path = os.path.join(args.log_dir, log_filename)
                
                if os.path.exists(log_path):
                    try:
                        os.remove(log_path)
                        removed_count += 1
                        print('Delete partial log file:', log_filename)
                    except OSError as e:
                        print(f"Error deleting log file {log_path}: {e}")
            
            if removed_count > 0:
                print(f"Cleaned up {removed_count} partial log files from previous runs.")

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
        start_task_time = time.time()
        args.instr_id = instr["instr_id"]
        global_planner = GlobalPlanner(args=args)
        action_generator = ActionGenerator(env=val_env, args=args, partner=global_planner)

        message_2D = action_generator.test()
        end_task_time = time.time()
        duration = end_task_time - start_task_time
        traj = message_2D['traj']
        status = message_2D['status']
        replanned = message_2D['replanned']

        pred = {'instr_id': instr['instr_id'], 'status': status, 'trajectory': traj['path'], 'a_t': traj['actions'], 'replanned': replanned, 'running_time': round(duration, 3)}
       
        with open(os.path.join(args.pred_dir, str(i + 1) + '_' + instr['instr_id'] + '.json'), 'w') as f:
            json.dump(pred, f, ensure_ascii=False)
            print(f"record file to {os.path.join(args.pred_dir, str(i + 1) + '_' + instr['instr_id'] + '.json')}")

    print('================== Evaluation is finished! ==================')
        
        

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs(args.pred_dir, exist_ok=True)

    set_random_seed(args.seed)
    val_env = build_dataset(args)
    start_time = time.time()
    valid(args, val_env)
    print_metric(args, val_env, start_time)


if __name__ == '__main__':
    main()