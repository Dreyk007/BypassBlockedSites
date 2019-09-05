# СТАРАЯ (к тому же - велосипед) кастомная функция для чтения\записи текстовых файлов
def RW_File(mode, filename, data=None, read_dict=0):
    # Определяем переменную с разделителем:
    sep = ':*:'
    # Открываем файл:
    file = open(filename, mode)

    # Читаем полученные данные из файла:
    if mode == 'r':
        # Если требуется конвертирования данных в словарь с разделителем "sep":
        if read_dict == 1:
            data = {}
            # Читаем файл построчно и сохраняем строки в список:
            dict_list = [row.strip() for row in file]
            # Преобразуем список в словарь используя разделитель:
            for str_with_sep in dict_list:
                # Функция split возвращает 2 значения (в данном случае) из одной строки:
                key, value = str_with_sep.split(sep)
                # print(key,value)
                # Записываем данные в словарь:
                data[key] = value
        else:
            # Просто получаем строки в список:
            data = [row.strip() for row in file]

        # Закрываем файл:
        file.close()
        # Возвращаем полученные данные:
        return data

    # Записываем полученные данные в файл (с перезаписью):
    elif mode == 'w':
        # Определяем тип данных и записываем их в файл:
        if type(data) == list:
            # Список:
            for i in data:
                file.write(str(i) + '\n')
        elif type(data) == str or type(data) == int:
            # Строка:
            file.write(str(data) + '\n')
        elif type(data) == dict:
            # В случае, если тип данных - словарь, записываем ключ + значение через разделитель:
            for key in data:
                file.write(str(key) + sep + str(data[key]) + '\n')
        else:
            # Если что-то не так с типом данных, закрываем файл и вызываем исключение:
            file.close()
            print("ОШИБКА типа данных (при записи в файл)!")
            raise ValueError

    # Записываем полученные данные в файл (без перезаписи, методом добавления):
    elif mode == 'a':
        # Определяем тип данных и записываем их в файл:
        if type(data) == list:
            # Список:
            for i in data:
                file.write(str(i) + '\n')
        elif type(data) == str or type(data) == int:
            # Строка:
            file.write(str(data) + '\n')
        elif type(data) == dict:
            # В случае, если тип данных - словарь, записываем ключ + значение через разделитель:
            for key in data:
                file.write(str(key) + sep + str(data[key]) + '\n')
        else:
            # Если что-то не так с типом данных, закрываем файл и вызываем исключение:
            file.close()
            print("ОШИБКА типа данных (при записи в файл)!")
            raise ValueError

    # Закрываем файл:
    file.close()
