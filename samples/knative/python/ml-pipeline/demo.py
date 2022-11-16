import json

test_data_file_path = 'dataset/Digits_Test.txt'
train_data_file_path = 'dataset/Digits_Train.txt'


def dump_file_to_kv(path):
    with open(path) as f:
        content = json.dumps(f.readlines())
        return content


content = dump_file_to_kv(train_data_file_path)

print(len(content))
