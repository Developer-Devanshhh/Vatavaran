import pickle

config = pickle.load(open('model_config.pkl', 'rb'))
features = config.get('feature_columns', [])
print('Total features:', len(features))
print('\nAll features:')
for i, f in enumerate(features, 1):
    print(f'{i}. {f}')
