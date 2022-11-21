import split
import extract

if __name__ == '__main__':
    result = split.lambda_handler(src_video=3, partition_num=3)
    events = result["detail"]["indeces"]
    return_list = []

    for event in events:  # Should run in parallel
        extract_result = extract.lambda_handler(event)
        return_list.append(extract_result)

    print(len(return_list))
