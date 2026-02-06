import numpy as np
import json
from tensorflow.keras.models import load_model

# Load trained model
model = load_model("model.h5")

# Load charset
with open("charset.json", "r") as f:
    char_to_ix = json.load(f)

ix_to_char = {v: k for k, v in char_to_ix.items()}

SEQ_LENGTH = 20

def generate_password(seed="password", length=12):
    """
    Generates realistic-looking password using trained ML model
    """

    seed = seed[:SEQ_LENGTH].ljust(SEQ_LENGTH)
    result = seed
    output = seed.strip()

    for _ in range(length):
        x = np.array([[char_to_ix.get(c, 0) for c in result]])
        x = x.reshape(1, SEQ_LENGTH, 1)

        prediction = model.predict(x, verbose=0)
        index = np.argmax(prediction)

        char = ix_to_char[index]
        output += char
        result = result[1:] + char

    return output
