import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Activation, Flatten
from tensorflow.keras.layers import Conv1D, MaxPooling1D
from tensorflow.keras.utils import to_categorical
from datetime import datetime

NUM_CLASSES = 4

df = pd.read_csv('micerace/training_data_full.csv')
winners = df['winner_position_ndx']

clean_df = df.drop(
    columns=['winner_position_ndx',
             'mice',
             'winner_name',
             'race_id',
             'mouse_0_name',
             'mouse_1_name',
             'mouse_2_name',
             'mouse_3_name'])

clean_df = clean_df.fillna(value=0)

y_data = winners.to_numpy(dtype=int)
x_data = clean_df.to_numpy(dtype=float)
x_data = np.expand_dims(x_data, axis=2)


(x_train, y_train) = (x_data[:int(len(x_data)*0.7)], to_categorical(y_data[:int(len(y_data)*0.7)], num_classes=4))
(x_test, y_test) = (x_data[int(len(x_data)*0.7):], to_categorical(y_data[int(len(y_data)*0.7):], num_classes=4))

model = Sequential()
model.add(Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=x_train.shape[1:]))
model.add(Conv1D(filters=64, kernel_size=3, activation='relu'))
model.add(Dropout(0.5))
model.add(MaxPooling1D(pool_size=2))
model.add(Flatten())
model.add(Dense(100, activation='relu'))
model.add(Dense(NUM_CLASSES, activation='softmax'))
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

model.fit(x_train, y_train, batch_size=32, epochs=50, validation_data=(x_test, y_test), shuffle=True)
model.save(f'model-{datetime.utcnow()}.h5')
