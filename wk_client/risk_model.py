import pandas as pd
from xgboost import XGBClassifier
import os


class XGB_classifier:
    
    def __init__(self):
        retro_data = pd.read_csv(os.path.abspath('wk_client/retro_data.csv'))

        y = retro_data['outcome']

        X = retro_data.drop(columns=['Unnamed: 0', 'outcome', 'loan_duration', 'company__opinion', 'company__region'])

        self.xgboost = XGBClassifier(learning_rate=0.1, n_estimators=100, max_depth=5,
                                min_child_weight=3, gamma=0.2, subsample=0.6, colsample_bytree=1.0,
                                objective='binary:logistic', nthread=4, scale_pos_weight=1)

        self.xgboost.fit(X, y)

    def _predict(self, customer_data):
        return self.xgboost.predict(customer_data)
    