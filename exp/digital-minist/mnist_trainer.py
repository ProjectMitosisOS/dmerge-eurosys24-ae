# 导入所需的库和数据集
import lightgbm as lgb
from sklearn.metrics import accuracy_score

import numpy as np

train_data = np.genfromtxt("dataset/Digits_Train.txt", delimiter='\t')
test_data = np.genfromtxt('dataset/Digits_Test.txt', delimiter='\t')

y_train = train_data[:, 0]
X_train = train_data[:, 1:train_data.shape[1]]

y_test = test_data[:, 0]
X_test = test_data[:, 1:test_data.shape[1]]

train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test)

params = {
    'boosting_type': 'gbdt',
    'objective': 'multiclass',
    'num_class': 10,
    'metric': 'multi_logloss',
    'num_leaves': 50,
    'learning_rate': 0.05,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'feature_fraction': 0.9
}

model = lgb.train(params, train_data, valid_sets=[train_data, test_data],
                  num_boost_round=200, early_stopping_rounds=10)

model.save_model('mnist_model.txt')

model = lgb.Booster(model_file='mnist_model.txt')

y_pred = model.predict(X_test)
y_pred = [list(x).index(max(x)) for x in y_pred]

print(y_pred)

accuracy = accuracy_score(y_test, y_pred)
print('Accuracy:', accuracy)
