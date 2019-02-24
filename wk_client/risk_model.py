import numpy as np
import pandas as pd
from xgboost import XGBClassifier
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

retro_data = pd.read_csv(os.path.abspath('wk_client/retro_data.csv'))

y = retro_data['outcome']

X = retro_data.drop(columns=['Unnamed: 0', 'outcome','loan_duration','company__opinion','company__region'])

# check accuracy of the xgboost model

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

xgboost = XGBClassifier(learning_rate=0.1, n_estimators=100, max_depth=5,
                        min_child_weight=3, gamma=0.2, subsample=0.6, colsample_bytree=1.0,
                        objective='binary:logistic', nthread=4, scale_pos_weight=1)

xgboost.fit(X_train, y_train)

y_pred = xgboost.predict(X_test)

accuracy_score(y_test, y_pred)

# run model on full set of data

xgboost.fit(X, y)

