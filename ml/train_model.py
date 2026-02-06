import numpy as np
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.utils import to_categorical

# Load password dataset
with open("passwords.txt", "r") as f:
    text = f.read()

# Create character mappings
chars = sorted(list(set(text)))
char_to_ix = {c: i for i, c in enumerate(chars)}
ix_to_char = {i: c for i, c in enumerate(chars)}

# Save charset for later generation
with open("charset.json", "w") as f:
    json.dump(char_to_ix, f)

SEQ_LENGTH = 20

X = []
y = []

for i in range(len(text) - SEQ_LENGTH):
    seq = text[i:i + SEQ_LENGTH]
    target = text[i + SEQ_LENGTH]

    X.append([char_to_ix[c] for c in seq])
    y.append(char_to_ix[target])

X = np.array(X)
y = to_categorical(y)

# Build model
model = Sequential()
model.add(LSTM(128, input_shape=(SEQ_LENGTH, 1)))
model.add(Dense(len(chars), activation="softmax"))

model.compile(
    loss="categorical_crossentropy",
    optimizer="adam"
)

print("Training started...")
model.fit(X.reshape(X.shape[0], X.shape[1], 1), y, epochs=20, batch_size=64)

# Save model
model.save("model.h5")

print("Training finished.")
print("model.h5 and charset.json created")
