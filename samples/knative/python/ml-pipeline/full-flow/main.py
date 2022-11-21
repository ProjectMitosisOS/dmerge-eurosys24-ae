from pca import PCA
import train
import combine

if __name__ == '__main__':
    out_file_name, return_dic = PCA(partition_num=4)
    events = return_dic["detail"]["indeces"]

    # Parallel
    combine_input_events = []
    print(len(events))
    for event in events:
        return_dic = train.handler(event)
        combine_input_events.append(return_dic)

    # Reduce
    result = combine.handler(combine_input_events)
    print("result ==========")
    print(result)
