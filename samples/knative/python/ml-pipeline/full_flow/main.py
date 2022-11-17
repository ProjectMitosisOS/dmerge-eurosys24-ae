from pca import PCA
import train
import combine

if __name__ == '__main__':
    out_file_name, return_dic = PCA()
    event = return_dic["detail"]["indeces"][-1]
    return_dic = train.handler(event)
    event = [return_dic]
    result = combine.handler(event)
    print("result ==========")
    print(result)
