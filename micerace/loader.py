import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Activation, Flatten
from tensorflow.keras.layers import Conv1D, MaxPooling1D
from tensorflow.keras import optimizers
#from tf.keras import backend as K

EPOCHS = 2000
NUM_CLASSES = 4
BATCH_SIZE = 32


df = pd.read_csv('micerace/training_data_full.csv')
winners = df['winner_position_ndx']
clean_df = df.drop(
    columns=[
        'winner_position_ndx', 'mice', 'winner_name', 'race_id', 'mouse_0_name', 'mouse_1_name', 'mouse_2_name', 'mouse_3_name'])


y_data = winners.to_numpy(dtype=int)
x_data = clean_df.to_numpy(dtype=float)
x_data = np.expand_dims(x_data, axis=2)


(x_train, y_train) = (x_data[:int(len(x_data)*0.7)], y_data[:int(len(y_data)*0.7)])
(x_test, y_test) = (x_data[int(len(x_data)*0.7):], y_data[int(len(y_data)*0.7):])

#(x_data[int(len(x_data)*0.8):]], y_data[:70]), (x_data[70:], y_data[70:])


model = Sequential()
print(x_train.shape)
print(x_train.shape[1:])

model.add(Conv1D(100, 100, padding='same', input_shape=x_train.shape[1:])) #x_train.shape[1:]))
model.add(Activation('relu'))
model.add(Conv1D(100, 100))
model.add(Activation('relu'))
model.add(MaxPooling1D(pool_size=1))
model.add(Dropout(0.25))

model.add(Conv1D(100, 100, padding='same'))
model.add(Activation('relu'))
model.add(Conv1D(100, 1))
model.add(Activation('relu'))
model.add(MaxPooling1D(pool_size=1))
model.add(Dropout(0.25))

model.add(Flatten())
model.add(Dense(512))
model.add(Activation('relu'))
model.add(Dropout(0.5))
model.add(Flatten())

model.add(Dense(NUM_CLASSES))
model.add(Activation('softmax'))

opt = optimizers.SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
model.compile(loss='sparse_categorical_crossentropy', optimizer=opt, metrics=['accuracy'])

model.fit(x_train, y_train, batch_size=BATCH_SIZE, epochs=EPOCHS, validation_data=(x_test, y_test), shuffle=False)
