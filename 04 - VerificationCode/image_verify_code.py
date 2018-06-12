import tesserocr

from PIL import Image

# ################## 入门级 ########################


def basic():
    image = Image.open('code.jpg')
    result = tesserocr.image_to_text(image)
    print(result)

# ################## 灰度化 ########################


def gray():
    image = Image.open('code.jpg')
    image = image.convert('L')
    image.show()

# ################## 二值化 ########################


def binarization_default():
    # 二值化默认阈值为127
    image = Image.open('code.jpg')
    image = image.convert('1')
    image.show()


def binarization(threshold):
    image = Image.open('code.jpg')
    image = image.convert('L')
    table = []
    for i in range(256):
        if i < threshold:
            table.append(0)
        else:
            table.append(1)
    image = image.point(table, '1')
    image.show()

# ################## 好一点 ########################


def advance(threshold):
    image = Image.open('code.jpg')

    image = image.convert('L')
    result = tesserocr.image_to_text(image)
    print('灰度化结果：', result)

    table = []
    for i in range(256):
        if i < threshold:
            table.append(0)
        else:
            table.append(1)
    image = image.point(table, '1')
    result = tesserocr.image_to_text(image)
    print('二值化结果：', result)

# ################## 测 试 ########################


if __name__ == '__main__':
    # basic()
    # gray()
    # binarization_default()
    # binarization(80)
    advance(150)
