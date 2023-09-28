import split
import trainer
if __name__ == '__main__':
    return_dic = split.lambda_handler({
        'bundle_size': 8,
        'Network_Bound': 0,
        'skew': 1
    })
    events = return_dic["detail"]["indeces"]

    # Parallel
    rets = []
    for event in events:
        return_dic = trainer.lambda_handler(event)
        rets.append(return_dic)
    print(rets)