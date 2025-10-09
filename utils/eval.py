import numpy as np
import os
import time
import json

def cal_dtw(shortest_distances, prediction, reference, success=None, threshold=3.0):
    dtw_matrix = np.inf * np.ones((len(prediction) + 1, len(reference) + 1))
    dtw_matrix[0][0] = 0
    for i in range(1, len(prediction)+1):
        for j in range(1, len(reference)+1):
            best_previous_cost = min(
                dtw_matrix[i-1][j], dtw_matrix[i][j-1], dtw_matrix[i-1][j-1])
            cost = shortest_distances[prediction[i-1]][reference[j-1]]
            dtw_matrix[i][j] = cost + best_previous_cost

    dtw = dtw_matrix[len(prediction)][len(reference)]
    ndtw = np.exp(-dtw/(threshold * len(reference)))
    if success is None:
        success = float(shortest_distances[prediction[-1]][reference[-1]] < threshold)
    sdtw = success * ndtw

    return {
        'DTW': dtw,
        'nDTW': ndtw,
        'SDTW': sdtw
    }

def cal_cls(shortest_distances, prediction, reference, threshold=3.0):
    def length(nodes):
      return np.sum([
          shortest_distances[a][b]
          for a, b in zip(nodes[:-1], nodes[1:])
      ])

    coverage = np.mean([
        np.exp(-np.min([  # pylint: disable=g-complex-comprehension
            shortest_distances[u][v] for v in prediction
        ]) / threshold) for u in reference
    ])
    expected = coverage * length(reference)
    score = expected / (expected + np.abs(expected - length(prediction)))
    return coverage * score
    

def print_metric(args, val_env, start_time):
    # evaluation
    results = []
    for file in os.listdir(args.pred_dir):
        with open(os.path.join(args.pred_dir, file), 'r') as f:
            data = f.readline()
            pred = json.loads(data)
            results.append(pred)
    score_summary, _, _ = val_env.eval_metrics(results, args.dataset)
    loss_str = "Current time: %s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())) + ", Env name: %s" % val_env.name
    for metric, val in score_summary.items():
        loss_str += ', %s: %.2f' % (metric, val)

    with open(os.path.join(args.log_dir, 'valid.txt'), 'a') as f:
        f.write(loss_str)
        f.write("\n")
        f.write(val_env.name + ' cost time: %.2fs' % (time.time() - start_time))
        f.write("\n\n")

    print(loss_str) 