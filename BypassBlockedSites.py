from datetime import datetime
from ipaddress import ip_network, collapse_addresses
from os import path
from subprocess import check_output, run, PIPE
from sys import exit
from time import sleep

from requests import get

from MyFuncs import RW_File


def parsing_ips_from_url():
    # Сбор заблокированных IP-адресов из источников (грязный "парсинг")
    # Возвращает: оптимизированный список заблокированных IP-адресов и подсетей из двух исчтоников.
    global LOG

    ips_w_pre = []

    try:
        ips_w_pre_s_0 = []
        raw_ips = get(SOURCE_URL_0)
        splited_by_n = raw_ips.text.split('\n')

        for i in splited_by_n:
            if len(i) != 0 and i[0] != '#' and 'route ' in i:
                i = i[i.find('"') + 1:i.rfind('"')].split(' ')[1:]
                if len(i) > 1:
                    ip = i[0]
                    mask = i[1]
                    ip_w_pre = ip_network(ip + '/' + mask)
                    ips_w_pre_s_0.append(ip_w_pre)

        if not ips_w_pre_s_0:
            raise ValueError
        else:
            ips_w_pre = ips_w_pre + ips_w_pre_s_0
    except Exception as get_source_error:
        LOG.append(str(datetime.now()) + ' : Возникла ОШИБКА в процессе получения маршрутов. Маршруты из источника 1 '
                                         'не получены:\n' + str(get_source_error))
        pass

    try:
        ips_w_pre_s_1 = []
        raw_ips = get(SOURCE_URL_1)
        splited_by_n = raw_ips.text.split('\n')
        for i in splited_by_n:
            ip_w_pre = ip_network(i)
            ips_w_pre_s_1.append(ip_w_pre)

        if not ips_w_pre_s_1:
            raise ValueError
        else:
            ips_w_pre = ips_w_pre + ips_w_pre_s_1
    except Exception as get_source_error:
        LOG.append(str(datetime.now()) + ' : Возникла ОШИБКА в процессе получения маршрутов. Маршруты из источника 2 '
                                         'не получены:\n' + str(get_source_error))
        pass

    if not ips_w_pre:
        LOG.append(str(datetime.now()) + ' : ОШИБКА. Не удалось получить маршруты не из одного источника. '
                                         'Завершаем работу скрипта.\n')

        exit(1)
    else:
        collapsed_ips_w_pre_net = list(collapse_addresses(ips_w_pre))
        ips_w_pre_str = net_convert(collapsed_ips_w_pre_net, to='str')

        RW_File(mode='w', filename=CACHED_ROUTES_FILENAME, data=ips_w_pre_str)

        return collapsed_ips_w_pre_net


def delete_routes(cur_routes):
    # Удаление заданных маршрутов из системы
    for i in cur_routes:
        run(COMMAND_TO_DELETE_ROUTE + i + TO_NULL_DEVICE, stderr=PIPE, shell=True, check=False)


def add_routes(ips_w_pre):
    # Добавление заданных маршрутов в систему
    for i in ips_w_pre:
        run(COMMAND_TO_ADD_ROUTE + i + ' ' + GW_IP + TO_NULL_DEVICE, stderr=PIPE, shell=True, check=False)


def get_cur_routes():
    # Получение текущих маршрутов из системы путём грязного "парсинга" вывода консоли
    # Возвращает: текущие маршруты установленные в системе
    cur_routes = check_output(COMMAND_TO_SHOW_CUR_ROUTES, encoding=ENCODING, shell=True)
    c0 = cur_routes.find('IPv4 таблица маршрута')
    c1 = cur_routes.find('Постоянные маршруты:', c0)
    c2 = cur_routes.find('===========================================================================', c1)
    splited_cur_routes = cur_routes[c1:c2].split('\n')

    cur_routes_net = []
    for i in splited_cur_routes:
        i = i.split()
        if len(i) > 2 and i[0] != '0.0.0.0' and i[2] == GW_IP:
            i = i[0] + '/' + i[1]
            cur_routes_net.append(ip_network(i))

    cur_routes_net = sorted(cur_routes_net)

    return cur_routes_net


def net_convert(net, to):
    # Конвертация IP-адресов и подсетей из объектов библиотеки "ipaddress" в строку и обратно
    # Возвращает объекты или строки в виде списка
    if to == 'net':
        return sorted([ip_network(i) for i in net])
    elif to == 'str':
        return [str(i) for i in sorted(net)]
    else:
        raise ValueError


def diff_in_routes(cur_routes, ips_w_pre):
    # Вычисляем разницу в текущих и предоставленных (новых) маршрутах включая оптимизацию IP-адресов и подсетей.
    # Возвращает: новые адреса, которые нужно добавить к текущим (в систему) и адреса, которые нужно удалить.
    global LOG

    def int_diff_in_routes(int_cur_routes, int_ips_w_pre):
        diff = list(set(int_cur_routes).symmetric_difference(set(int_ips_w_pre)))
        int_new_routes = []
        int_to_delete_routes = []
        for y in diff:
            if y not in int_cur_routes:
                int_new_routes.append(y)
            elif y not in int_ips_w_pre:
                int_to_delete_routes.append(y)

        return int_new_routes, int_to_delete_routes

    new_routes, to_delete_routes = int_diff_in_routes(cur_routes, ips_w_pre)

    to_optimize = list(set(cur_routes) - set(to_delete_routes)) + new_routes
    collapsed_new_routes = collapse_addresses(to_optimize)

    new_routes, to_delete_routes = int_diff_in_routes(cur_routes, collapsed_new_routes)

    new_routes = net_convert(new_routes, to='str')
    to_delete_routes = net_convert(to_delete_routes, to='str')

    if new_routes:
        LOG.append(str(datetime.now()) + ' : Маршруты для добавления: ' + ', '.join(new_routes))
    else:
        LOG.append(str(datetime.now()) + ' : Нет новых маршрутов для добавления.')

    if to_delete_routes:
        LOG.append(str(datetime.now()) + ' : Маршруты для удаления: ' + ', '.join(to_delete_routes))
    else:
        LOG.append(str(datetime.now()) + ' : Нет маршрутов для удаления.')

    return new_routes, to_delete_routes


def check_connection():
    # Проверка соединения с VPN-сервером
    global LOG

    c = 0
    check_connection_to_vpn = 1
    while check_connection_to_vpn != 0:
        c += 1
        check_connection_to_vpn = run(COMMAND_TO_PING, stderr=PIPE, shell=True).returncode
        if check_connection_to_vpn != 0 and c > 5:
            LOG.append(str(datetime.now()) + ' : Ждём 5 секунд... нет пинга до VPN-сервера.')
            sleep(5)
        elif check_connection_to_vpn != 0 and c <= 5:
            LOG.append(str(datetime.now()) + ' : Ждём 1 секунду... нет пинга до VPN-сервера.')
            sleep(1)
    LOG.append(str(datetime.now()) + ' : Есть пинг до VPN-сервера.')


def write_log():
    # Изобретаем велосипед для записи лога (по правильному: нужно использовать готовые решения для этого)
    if path.isfile(LOG_FILENAME):
        if len(RW_File(mode='r', filename=LOG_FILENAME)) > 1000:
            log_mode = 'w'
        else:
            log_mode = 'a'
    else:
        log_mode = 'w'

    RW_File(mode=log_mode, filename=LOG_FILENAME, data=LOG)


if __name__ == "__main__":
    # Выполнение программы

    LOG_FILENAME = 'routes_change.log'
    LOG = list()
    LOG.append(str(datetime.now()) + ' : Скрипт запущен.')

    # Кодировка для работы с терминалом Windows
    ENCODING = 'IBM866'
    # IP-адрес VPN-шлюза
    GW_IP = '10.0.1.1'
    # Источники заблокированных IP-адресов и подсетей
    SOURCE_URL_0 = 'https://raw.githubusercontent.com/zhovner/zaborona_help/master/config/openvpn/ccd/DEFAULT'
    SOURCE_URL_1 = 'https://uablacklist.net/subnets.txt'
    # Кеш заблокированных адресов из источников
    CACHED_ROUTES_FILENAME = 'last_routed_ips.lst'
    # Команды для операций с маршрутами в системе
    TO_NULL_DEVICE = ' > nul'
    COMMAND_TO_PING = 'ping -n 1 ' + GW_IP + TO_NULL_DEVICE
    COMMAND_TO_ADD_ROUTE = 'route -p ADD '
    COMMAND_TO_DELETE_ROUTE = 'route DELETE '
    COMMAND_TO_SHOW_CUR_ROUTES = 'route PRINT'

    try:
        # Проверяем соединение с VPN-сервером
        check_connection()

        # Проверяем наличие файла с маршрутами, которые нужно добавить
        if path.isfile(CACHED_ROUTES_FILENAME):
            LOG.append(str(datetime.now()) + ' : Файл с подсетями на месте.')
            # Превращаем адреса в объекты для дальнейшей оптимизации
            IPS_W_PRE = net_convert(RW_File(mode='r', filename=CACHED_ROUTES_FILENAME), to='net')
        else:
            LOG.append(str(datetime.now()) + ' : Нет файла с подсетями. Запускаем процесс его формирования.')
            IPS_W_PRE = parsing_ips_from_url()

        LOG.append(str(datetime.now()) + ' : Начинаем получать текущие маршруты.')
        CUR_ROUTES = get_cur_routes()
        LOG.append(str(datetime.now()) + ' : Закончили получать текущие маршруты.')

        # Проверяем соответствуют ли текущие маршруты в системе предоставленным в файле с кешем
        if CUR_ROUTES != IPS_W_PRE:

            # print(CUR_ROUTES)
            # print(IPS_W_PRE)

            LOG.append(str(datetime.now()) + ' : Текущие маршруты не соответствуют предоставленным в файле. '
                                             'Начинаем применение маршрутов. Вычисляем изменения в маршрутах.')
            NEW_ROUTES, TO_DELETE_ROUTES = diff_in_routes(CUR_ROUTES, IPS_W_PRE)
            LOG.append(str(datetime.now()) + ' : Закончили вычисление изменений. Начинаем удалять ненужные маршруты.')
            delete_routes(TO_DELETE_ROUTES)
            LOG.append(str(datetime.now()) + ' : Закончили удаление ненужных маршрутов. '
                                             'Начинаем добавление новых маршрутов.')
            add_routes(NEW_ROUTES)
            LOG.append(str(datetime.now()) + ' : Закончили добавление новых маршрутов. Закончили применение маршрутов.')
        else:
            LOG.append(str(datetime.now()) + ' : Текущие маршруты идентичны полученным из файла. Применение маршрутов '
                                             'не требуется.')

        # Обновляем файл с маршрутами из источников
        LOG.append(str(datetime.now()) + ' : Начинаем формировать обновлённый файл с маршрутами.')
        NEW_IPS_W_PRE = parsing_ips_from_url()
        LOG.append(str(datetime.now()) + ' : Закончили формировать обновлённый файл с маршрутами.')

        # Проверяем есть ли разница между текущим файлом с маршрутами и обновлённым
        # В случае наличия обновлений - применяем их к системе наиболее оптимальным образом
        if NEW_IPS_W_PRE != IPS_W_PRE:
            LOG.append(str(datetime.now()) + ' : Новый файл с маршрутами содержит ОБНОВЛЕНИЯ. Приступаем к добавлению '
                                             'новых маршрутов в систему. Вычисляем изменения в маршрутах.')
            NEW_ROUTES, TO_DELETE_ROUTES = diff_in_routes(IPS_W_PRE, NEW_IPS_W_PRE)
            LOG.append(str(datetime.now()) + ' : Закончили вычисление изменений. Начинаем удалять ненужные маршруты.')
            delete_routes(TO_DELETE_ROUTES)
            LOG.append(str(datetime.now()) + ' : Закончили удаление ненужных маршрутов. '
                                             'Начинаем добавление новых маршрутов.')
            add_routes(NEW_ROUTES)
            LOG.append(str(datetime.now()) + ' : Закончили добавлять обновлённые маршруты в систему.')
        else:
            LOG.append(str(datetime.now()) + ' : Новый файл с маршрутами идентичен текущему. Обновлений нет.')

        exit(0)

    except Exception as ERROR:
        # Обрабатываем непредвиденные ошибки
        LOG.append(str(datetime.now()) + ' : ВОЗНИКЛА НЕПРЕДВИДЕННАЯ ОШИБКА:\n' + str(ERROR))
        exit(1)

    finally:
        # Записываем лог
        LOG.append(str(datetime.now()) + ' : Завершаем работу скрипта.\n')
        write_log()
