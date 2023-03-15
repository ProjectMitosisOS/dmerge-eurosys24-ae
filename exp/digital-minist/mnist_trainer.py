# 导入所需的库和数据集
import lightgbm as lgb
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

digits = load_digits()

# 将数据集分成训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(digits.data, digits.target, test_size=0.2)

# 将数据集转换为LightGBM所需的格式
train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test)

# 设置LightGBM的参数
params = {
    'boosting_type': 'gbdt',
    'objective': 'multiclass',
    'num_class': 10,
    'metric': 'multi_logloss',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9
}

# 训练模型
model = lgb.train(params, train_data, valid_sets=[train_data, test_data],
                  num_boost_round=10, early_stopping_rounds=10)

# 保存模型
model.save_model('mnist_model.txt')

# 加载模型
model = lgb.Booster(model_file='mnist_model.txt')

# 在测试集上进行预测
y_pred = model.predict(X_test)
y_pred = [list(x).index(max(x)) for x in y_pred]  # 将预测的概率转换为类别

# 输出预测结果
print(y_pred)

# 计算预测的正确率
accuracy = accuracy_score(y_test, y_pred)
print('Accuracy:', accuracy)
