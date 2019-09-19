import os
import shutil
from datetime import datetime
from random import shuffle

import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Activation, Flatten, Embedding, SpatialDropout1D, LSTM, LeakyReLU
from tensorflow.keras.layers import Conv1D, MaxPooling1D, MaxPooling2D
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import optimizers
from tensorflow.keras import regularizers

NUM_CLASSES = 4

df = pd.read_csv('training_data/training-latest.csv')
winners = df['winner_position_ndx']

clean_df = df.drop(
    columns=['winner_position_ndx',
             'mice',
             'winner_name',
             'winner_name_id',
             'race_id',
             'mouse_0_name',
             'mouse_1_name',
             'mouse_2_name',
             'mouse_3_name'])

clean_df = clean_df.fillna(value=-1).sample(frac=1).sample(frac=1)

x_data = clean_df.to_numpy(dtype=float)
x_data = np.expand_dims(x_data, axis=2)
y_data = winners.to_numpy(dtype=int)
y_data = to_categorical(y_data, num_classes=4)

model = Sequential()
model.add(Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=x_data.shape[1:]))
model.add(Conv1D(filters=64, kernel_size=3, activation='relu'))
model.add(Dropout(0.5))
model.add(MaxPooling1D(pool_size=2))
model.add(Flatten())
model.add(Dense(100, activation='relu'))
model.add(Dense(NUM_CLASSES, activation='softmax'))
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
model.fit(x_data, y_data, batch_size=40, epochs=100, validation_split=0.2, shuffle=True)
