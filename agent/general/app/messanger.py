import os
import cv2
import numpy as np


#Taken from https://github.com/W1LDN16H7/StegoCracker/blob/master/stego/StegoCracker
def to_bin(data):
    """
    Converts the data to binary

    """
    if isinstance(data, str):
        return ''.join([format(ord(i), "08b") for i in data])
    elif isinstance(data, bytes) or isinstance(data, np.ndarray):
        return [format(i, "08b") for i in data]
    elif isinstance(data, int) or isinstance(data, np.unit8):
        return format(data, "08b")
    else:
        raise TypeError("Type not supported")

#Taken from https://github.com/W1LDN16H7/StegoCracker/blob/master/stego/StegoCracker
def decode(image_name):
    """
    Decodes the secret data from the image
    - image_name: The name of the image
    - returns the secret data

    """
    if not os.path.exists(image_name):
        print("\033[92m[!] Image not found\033[00m")
        return
    print("\033[92mDecodingMode : On\033[0m \n\033[92m[*] Please wait...\033[0m \n\033[92m[*] Decoding...\033[0m")

    # read the image
    image = cv2.imread(image_name)
    binary_data = ""
    for row in image:
        for pixel in row:
            r, g, b = to_bin(pixel)
            binary_data += r[-1]
            binary_data += g[-1]
            binary_data += b[-1]
    # split by 8-bits
    all_bytes = [binary_data[i: i + 8] for i in range(0, len(binary_data), 8)]
    # remove all the stop bits
    # convert from bits to characters
    decoded_data = ""
    for byte in all_bytes:
        decoded_data += chr(int(byte, 2))
        if decoded_data[-5:] == "=====":
            break
    return decoded_data[:-5]



#Taken from https://github.com/W1LDN16H7/StegoCracker/blob/master/stego/StegoCracker
def encode(image_name, secret_data):
    """
    Encodes the secret data into the image
    - image_name: The name of the image
    - secret_data: The secret data to be encoded
    - return: The encoded image

    """
    if not os.path.exists(image_name):
        print("\033[92m[!] Image not found\033[00m")
        return

    # read the image
    image = cv2.imread(image_name)
    # maximum bytes to encode
    n_bytes = image.shape[0] * image.shape[1] * 3 // 8
    print("[*] Maximum bytes to encode:", n_bytes)
    if len(secret_data) > n_bytes:
        raise ValueError("[!] Insufficient bytes, need bigger image or less data.")

    print("\033[92mEncodingMode : On\033[0m \n\033[92m[*] Please wait...\033[0m \n\033[92m[*] Encoding...\033[0m")

    # add stopping criteria
    secret_data += "====="
    data_index = 0
    # convert data to binary
    binary_secret_data = to_bin(secret_data)
    # size of data to hide
    data_len = len(binary_secret_data)
    for row in image:
        for pixel in row:
            # convert RGB values to binary format
            r, g, b = to_bin(pixel)
            # modify the least significant bit only if there is still data to store
            if data_index < data_len:
                # least significant red pixel bit
                pixel[0] = int(r[:-1] + binary_secret_data[data_index], 2)
                data_index += 1
            if data_index < data_len:
                # least significant green pixel bit
                pixel[1] = int(g[:-1] + binary_secret_data[data_index], 2)
                data_index += 1
            if data_index < data_len:
                # least significant blue pixel bit
                pixel[2] = int(b[:-1] + binary_secret_data[data_index], 2)
                data_index += 1
            # if data is encoded, just break out of the loop
            if data_index >= data_len:
                break
    return image
