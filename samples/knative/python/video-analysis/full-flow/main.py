import split
import extract

if __name__ == '__main__':
    result = split.lambda_handler(src_video=2)
    events = result["detail"]["indeces"]

    extract_result = extract.lambda_handler(events[0])

