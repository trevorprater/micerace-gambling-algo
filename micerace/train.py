from collections import defaultdict

import numpy as np
import keras
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten
from keras.layers import Conv1D, MaxPooling1D


LABELED_DATA = defaultdict(list)

CLASSES = [0,1,2,3]

def load_data():
    train_x, train_y, test_x, test_y = list(), list(), list(), list()
    with open('training_data_full.csv') as infile:


        with open('/tmp/data.pk1', 'wb') as f:
            print("dumping data to pickle")
            pickle.dump(data, f)
            print("done pickling")

    for k in data:
        print('vectorizing {} classes'.format(k))
        test_data[k] = []
        test_data[k] = data[k][int(len(data[k]) * 0.8):]
        del data[k][int(len(data[k]) * 0.8):]
        class_ndx = CLASSES.index(k)
        for row in data[k]:
            vector = vector_replacement(row, VECTOR_LENGTH, ALPHA_DICT)
            train_x.append(np.asarray(vector))
            train_y.append(class_ndx)
        data[k] = []
        for row in test_data[k]:
            vector = vector_replacement(row, VECTOR_LENGTH, ALPHA_DICT)
            test_x.append(np.asarray(vector))
            test_y.append(class_ndx)
        test_data[k] = []

    del data
    del test_data
    print('done vectorizing')
    return (np.asarray(train_x), np.asarray(train_y)), (np.asarray(test_x), np.asarray(test_y))


batch_size = 32
num_classes = len(CLASSES)
epochs = 200

(x_train, y_train), (x_test, y_test) = load_data()

y_train = keras.utils.to_categorical(y_train, num_classes)
y_test = keras.utils.to_categorical(y_test, num_classes)

x_train = np.reshape(x_train, x_train.shape + (1,))
x_test = np.reshape(x_test, x_test.shape + (1,))

model = Sequential()

model.add(Conv1D(100, 100, padding='same', input_shape=x_train.shape[1:]))
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
model.add(Dense(num_classes))
model.add(Activation('softmax'))

opt = keras.optimizers.SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
model.compile(loss='categorical_crossentropy', optimizer=opt, metrics=['accuracy'])

model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs, validation_data=(x_test, y_test), shuffle=True)