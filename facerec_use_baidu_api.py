import redis
import time
import datetime
import requests
import json
import os
import shutil
from aip import AipFace
import base64
from PIL import Image

# pip install python-opencv
# pip install redis
# pip install requests
# pip install baidu-aip

HTTP_ENABLE = True  # True or False
EXIT_ON_HTTP_ERROR = True
HTTP_TIMEOUT = 5
RESIZE_WIDTH = 1600
RESIZE_HEIGHT = 1200
RESIZE_QUALITY = 75


def setup_redis_client(ip, port, db):
    print('setup redis client %s:%d, db_idx %d' % (ip, port, db))
    pool = redis.ConnectionPool(host=ip, port=port, db=db)
    r = redis.Redis(connection_pool=pool)
    return r


def setup_baidu_client(id, key, secret_key):
    print('setup baidu api client: id %s, key %s, secret_key %s' % (id, key, secret_key))
    return AipFace(id, key, secret_key)


def get_token_from_server(url, dev_no, app_id, app_secret):
    t = 'unkown'
    start_color = '0,0,0'
    end_color = '255,255,255'

    print('get token from server: dev_no %s, app_id %s, app_secret %s' % (dev_no, app_id, app_secret))
    payload = {'devNo': dev_no, 'appId': app_id, 'appSercert': app_secret}
    try:
        if HTTP_ENABLE:
            res = requests.get(url, params=payload, timeout=HTTP_TIMEOUT)
            if res.status_code == 200:
                json_res = json.loads(res.content)
                print(res.content)
                t = json_res['rows'][0]['token']
                start_color = json_res['rows'][0]['startColor']
                end_color = json_res['rows'][0]['endColor']
                print('got token: %s, start_color %s, end_color %s' % (t, start_color, end_color))
            else:
                if EXIT_ON_HTTP_ERROR:
                    print('http request error, exit!')
                    exit(-1)
        else:
            print('got token error! use default %s' % t)
            raise IOError
            # exit(-1)
    except Exception as e:
        print('get %s error!' % url)
        print(e)
        if EXIT_ON_HTTP_ERROR:
            print('http request error, exit!')
            exit(-1)
    finally:
        pass
    return t, start_color, end_color


def get_face_infos_from_server(url, dev_no, token):
    print('get face info from server: dev_no %s, token %s' % (dev_no, token))
    payload = {'devNo': dev_no, 'token': token}
    need_to_upload_face_lib = False
    try:
        if HTTP_ENABLE:
            res = requests.get(url, params=payload, timeout=HTTP_TIMEOUT)
            if res.status_code == 200:
                print(res.content)
                json_res = json.loads(res.content)
                face_infos = json_res['rows']
                for face_info in face_infos:
                    pic_url = FACE_PIC_HTTP_PREFIX + face_info['imageUrl1']
                    pic_url = pic_url.strip('\r\n')
                    pic_file = './face/' + str(face_info['userId']) + '.jpg'
                    face_info['pic_url'] = pic_url
                    face_info['pic_file'] = pic_file
                    if not os.path.isfile(pic_file):
                        print('begin get pic_url %s write to %s' % (pic_url, pic_file))
                        need_to_upload_face_lib = True
                        req = requests.get(pic_url)
                        with open(pic_file, "wb") as code:
                            code.write(req.content)
                    else:
                        print('already get pic_url %s write to %s' % (pic_url, pic_file))
                    print(face_info)
            else:
                if EXIT_ON_HTTP_ERROR:
                    print('http request error, exit!')
                    exit(-1)
        else:
            raise IOError
    except Exception as e:
        print('get %s error!' % url)
        print(e)
        # test code
        print('use test data!!!')
        face_infos = [{'userId': 33972}, {'userId': 33973}, {'userId': 34579}]
        # need_to_upload_face_lib = True  # test code
        for face_info in face_infos:
            pic_file = './face/' + str(face_info['userId']) + '.jpg'
            face_info['pic_file'] = pic_file
            print(face_info)
    finally:
        pass
    return face_infos, need_to_upload_face_lib


def upload_info_to_server(url, file_url, dev_no, token, people_str,best_pic_file_name, faceQualified, qualifiedUser,
                          changingQualified, score, color_b, color_g, color_r, color_str,
                          face_x, face_y, face_w, face_h, body_x, body_y, body_w, body_h,
                          suit_x, suit_y, suit_w, suit_h, status, sequence):
    ret = False
    payload = {'devNo': dev_no, 'token': token, 'sampleTime': people_str, 'faceQualified': faceQualified,
           'qualifiedUser': qualifiedUser, 'changingQualified': changingQualified, 'score': score,
               'color_b': color_b, 'color_g': color_g, 'color_r': color_r, 'color_str': color_str,
               'face_x': face_x, 'face_y': face_y, 'face_w': face_w, 'face_h': face_h,
               'body_x': body_x, 'body_y': body_y, 'body_w': body_w, 'body_h': body_h,
               'suit_x': suit_x, 'suit_y': suit_y, 'suit_w': suit_w, 'suit_h': suit_h,
               'status': status, 'sequence': sequence}
    try:
        if HTTP_ENABLE:
            res = requests.get(url, params=payload, timeout=HTTP_TIMEOUT)
            if res.status_code == 200:
                print(res.content)
                json_res = json.loads(res.content)
                upload_file_name = json_res['rows']
                code = json_res['code']
                desc = json_res['desc']
                print('upload_info: got upload_file_name: code %s, desc: %s, name %s' % (code, desc, upload_file_name))

                copy_file(best_pic_file_name, upload_file_name, RESIZE_WIDTH, RESIZE_HEIGHT, RESIZE_QUALITY)

                payload = {"file": upload_file_name}
                current_path = os.getcwd()
                cache_path = current_path + '\\cache\\'  # 将"cache"中的缩略图上传
                files = {
                    "file": open(cache_path+upload_file_name, "rb")
                }
                res = requests.post(file_url, payload, files=files)
                if res.status_code == 200:
                    print(res.content)
                    json_res = json.loads(res.content)
                    upload_file_name = json_res['rows']
                    code = json_res['code']
                    desc = json_res['desc']
                    ret = True
                    print('upload_file: code %s, desc: %s, name %s' % (code, desc, upload_file_name))
                else:
                    print('upload_file failed. %d' % res.status_code)
        else:
            ret = True
    except Exception as e:
        print('get %s error!' % UPLOAD_INFO_PREFIX)
        print(e)
    finally:
        pass
        # time.sleep(0.5)
        # os.remove(upload_file_name)  # 清缓存
    return ret


def get_base64_str_from_file(pic_file):
    f = open(pic_file, 'rb')  # 二进制方式打开图文件
    baidu_image_byte = base64.b64encode(f.read())  # 读取文件内容，转换为base64编码
    f.close()
    # print('baidu_image base64: %s' % baidu_image_byte)
    baidu_image = baidu_image_byte.decode('utf-8')
    return baidu_image


def upload_face_lib_to_baidu(client, groupId, face_infos):
    print('upload_face_lib_to_baidu: groupId %s' % (groupId))

    # 删除原始人脸库
    print('del face lib group %s' % (groupId))
    res = client.groupDelete(groupId)
    print(res)

    # 重新创建人脸库
    print('create face lib group %s' % (groupId))
    res = client.groupAdd(groupId)
    print(res)

    # 注册人脸
    for face_info in face_infos:
        userId = str(face_info['userId'])
        pic_file = face_info['pic_file']
        print('register face info [%s] for group %s, pic_file %s' % (userId, groupId, pic_file))
        image = get_base64_str_from_file(pic_file)
        imageType = 'BASE64'
        res = client.addUser(image, imageType, groupId, userId)
        print(res)


def copy_file(src_file, dst_file, width, height, quality):
    if width > 0 and height > 0:
        im = Image.open(src_file)
        # im.resize((width, height), Image.ANTIALIAS).save('\\cache\\%s' % dst_file, quality=quality)
        current_path = os.getcwd()
        cache_path = current_path + '\\cache\\'  # 缓存路径
        im.resize((width, height), Image.ANTIALIAS).save(cache_path+dst_file, quality=quality)  # 保存缩略图
    else:
        if os.path.isfile(src_file):
            shutil.copyfile(src_file, dst_file)
        else:
            print('%s not exists!' % src_file)


def judge_color(start_color, end_color, b, g, r):
    flag_judge_from_server_config = True
    b_float = float(b)
    g_float = float(g)
    r_float = float(r)
    if b_float < 0 or g_float < 0 or r_float < 0:
        print('b %f, ,g %f, r %f. invalid!\n' % (b_float, g_float, r_float))
        return -1

    if flag_judge_from_server_config:
        start_color_bgr = start_color.split(',')
        end_color_bgr = end_color.split(',')
        if len(start_color_bgr) < 3 or len(end_color_bgr) < 3:
            print('start_color %s, end_color %s . invalid!\n' % (start_color, end_color))
            return 0

        start_color_b = float(start_color_bgr[0])
        start_color_g = float(start_color_bgr[1])
        start_color_r = float(start_color_bgr[2])
        end_color_b = float(end_color_bgr[0])
        end_color_g = float(end_color_bgr[1])
        end_color_r = float(end_color_bgr[2])

        if start_color_b > b_float or end_color_b < b_float :
            print('start_color_b %f, b_float %f, end_color_b %f, invalid!\n' % (start_color_b, b_float, end_color_b))
            return 0
        if start_color_g > g_float or end_color_g < g_float :
            print('start_color_g %f, g_float %f, end_color_g %f, invalid!\n' % (start_color_g, g_float, end_color_g))
            return 0
        if start_color_r > r_float or end_color_r < r_float :
            print('start_color_r %f, r_float %f, end_color_r %f, invalid!\n' % (start_color_r, r_float, end_color_r))
            return 0
    return 1


def search_face(client, groupId, pic_file_name):
    print('search face for groupId %s, use pic %s' % (groupId, pic_file_name))

    user_list = []

    image = get_base64_str_from_file(pic_file_name)
    imageType = 'BASE64'
    res = client.search(image, imageType, groupId)
    print(res)
    if res['error_code'] == 0:
        user_list = res['result']['user_list']
    return user_list


if __name__ == '__main__':
    # begin config info
    DEV_NO = 'D002'
    APP_ID = 'YQ0003C0023'
    APP_SECRET = 'idsldsflfsdldfso2s2'

    BAIDU_APP_ID = '11675027'
    BAIDU_API_KEY = 'xGsLHB55rkZZsTI3oEyG3Spo'
    BAIDU_APP_SECRET_KEY = 'mMAVlQYfqkS4DqyGTwGqGPyymGGe70hX'
    BAIDU_APP_FACE_SCORE_MAX = 60
    BAIDU_APP_FACE_SCORE_OK = 90

    # HTTP_PREFIX = 'http://211.155.225.206:9005/aimgr/'
    HTTP_PREFIX = 'http://www.zhonshian.com/zsaai/aimgr/'
    # HTTP_PREFIX = 'http://202.91.244.43:9088/aimgr/'
    # HTTP_PREFIX = 'http://192.168.10.157:8082/zsaai/aimgr/'
    FACE_PIC_HTTP_PREFIX = 'http://114.55.75.34:85/'
    UPLOAD_INFO_PREFIX = HTTP_PREFIX + 'saveAiFaceQtRecord'
    DOWNLOAD_FACE_PREFIX = HTTP_PREFIX + 'downFace'
    UPLOAD_FILE_PREFIX = HTTP_PREFIX + 'uploadFile'
    DEVICE_INFO_PREFIX = HTTP_PREFIX + 'downAidevice'

    HEART_BEAT_TIME = 3600  # 默认一小时重新获取token

    REDIS_CLIENT_IP = '127.0.0.1'
    REDIS_CLIENT_PORT = 6379
    # 截图数据缓存
    REDIS_CLIENT_DB = 0
    PEOPLES_INDEX_SET_NAME = 'p_set'
    PEOPLE_INFO_PREFIX = 'p:'
    # end config info

    print('begin...')

    # setup redis
    r = setup_redis_client(REDIS_CLIENT_IP, REDIS_CLIENT_PORT, REDIS_CLIENT_DB)  # 截图数据缓存

    # setup baidu api client
    baidu_client = setup_baidu_client(BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_APP_SECRET_KEY)

    # get token & color
    token, start_color, end_color = get_token_from_server(DEVICE_INFO_PREFIX, DEV_NO, APP_ID, APP_SECRET)

    # 从server获取人脸数据库,以及是否需要向百度api更新人脸数据库
    print('***************************')
    face_infos, need_to_upload_face_lib = get_face_infos_from_server(DOWNLOAD_FACE_PREFIX, DEV_NO, token)
    print('00000000000000000000000000000000')
    groupId = DEV_NO
    if need_to_upload_face_lib:
        upload_face_lib_to_baidu(baidu_client, groupId, face_infos)
    else:
        print('no need to upload_face_lib_to_baidu')

    print('start to detect face...')
    detect_count_time = 0

    while True:  # 循环检测
        flags = False  # 是否有新数据

        # 打印, 判断是否重新获取token
        detect_count_time = detect_count_time + 1
        if detect_count_time % HEART_BEAT_TIME == 0:
            nowTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print('detect_count_time %d, get token again, time %s' % (detect_count_time, nowTime))
            token, start_color, end_color = get_token_from_server(DEVICE_INFO_PREFIX, DEV_NO, APP_ID, APP_SECRET)

        peoples = r.smembers(PEOPLES_INDEX_SET_NAME)  # 从redis获取是否有新的检测数据
        for people in peoples:
            flags = True

            people_str = people.decode('utf-8')  # 关键字,key,time值, 1534038575
            localtime = time.asctime(time.localtime(float(people_str)))  # 转换成本地时间字符串

            people_detect_count_str = PEOPLE_INFO_PREFIX + people_str
            people_detect_count = int(r.get(people_detect_count_str))  # 获取截图数量

            print('\nprocess people: time %s, %s, detect count %d' % (people_str, localtime, people_detect_count))

            # 初始化检测信息
            faceQualified = 0
            changingQualified = 0

            qualifiedUser = -1          # 最大匹配人脸的user_id
            max_face_match_count = 0    # 最大匹配人脸次数
            max_face_match_idx = -1     # 最匹配图片idx
            max_face_match_score = 0    # 最大匹配人脸score

            got_color_b = '-1'
            got_color_g = '-1'
            got_color_r = '-1'
            got_color_str = 'unknown'
            best_pic_idx = 0
            for face_info in face_infos:
                face_info['matchFaceCount'] = 0               # 最大匹配几次人脸
                face_info['matchFaceDetectIdx'] = -1          # 匹配此个人脸的图片idx
                face_info['maxFaceScore'] = 0                 # 最大匹配人脸分数

            score_ok_flag = False
            sequence = 0
            for pic_idx in range(people_detect_count):        # 遍历截图
                people_info_str = PEOPLE_INFO_PREFIX + people_str + ':' + str(pic_idx)         # redis key, hmset
                pic_file_name = r.hget(people_info_str, 'pic').decode('utf-8')                 # 获取截图文件名称
                pic_face_file_name = r.hget(people_info_str, 'pic_face').decode('utf-8')       # 获取人脸截图文件名称, TODO
                color_str = r.hget(people_info_str, 'color_str').decode('utf-8')               # 获取识别的衣服颜色
                # 获取识别的衣服颜色, BGR值
                color_b = r.hget(people_info_str, 'color_b').decode('utf-8')
                color_g = r.hget(people_info_str, 'color_g').decode('utf-8')
                color_r = r.hget(people_info_str, 'color_r').decode('utf-8')
                # 获取人脸位置
                face_x = r.hget(people_info_str, 'face_x').decode('utf-8')
                face_y = r.hget(people_info_str, 'face_y').decode('utf-8')
                face_w = r.hget(people_info_str, 'face_w').decode('utf-8')
                face_h = r.hget(people_info_str, 'face_h').decode('utf-8')
                # 获取人行位置
                body_x = r.hget(people_info_str, 'body_x').decode('utf-8')
                body_y = r.hget(people_info_str, 'body_y').decode('utf-8')
                body_w = r.hget(people_info_str, 'body_w').decode('utf-8')
                body_h = r.hget(people_info_str, 'body_h').decode('utf-8')
                # 获取衣服位置
                suit_x = r.hget(people_info_str, 'suit_x').decode('utf-8')
                suit_y = r.hget(people_info_str, 'suit_y').decode('utf-8')
                suit_w = r.hget(people_info_str, 'suit_w').decode('utf-8')
                suit_h = r.hget(people_info_str, 'suit_h').decode('utf-8')
                status = 2  # 默认不符合
                score = 0.0  # 默认评分为0，不匹配
                sequence += 1  # 截图序号
                r.hmset(people_info_str, {'status': status, 'score': score, 'sequence': sequence})
                print('111111111111111111111111111111111111111111111111111111111111111111111111')
                print('idx %d: pic %s, pic_face %s, color_str %s, color_bgr %s|%s|%s， face_position %s|%s|%s|%s， '
                      'body_position %s|%s|%s|%s， suit_position %s|%s|%s|%s, status %d, score %f, sequence %d' %
                      (pic_idx, pic_file_name, pic_face_file_name, color_str, color_b, color_g, color_r,
                       face_x, face_y, face_w, face_h, body_x, body_y, body_w, body_h, suit_x, suit_y, suit_w, suit_h,
                       status, score, sequence))
                if face_x + face_w > 1000 and face_x < 1700:
                    # 判断颜色是否符合要求
                    judge_color_idx = judge_color(start_color, end_color, color_b, color_g, color_r)
                    if judge_color_idx > 0:
                        changingQualified = 1
                        got_color_b = color_b
                        got_color_g = color_g
                        got_color_r = color_r
                        got_color_str = color_str
                        best_pic_idx = pic_idx                # best_pic_idx 设定为此截图的idx
                        print('idx %d: color valid ok, assume it as the pickup idx' % best_pic_idx)
                    else:
                        if changingQualified == 0:
                            got_color_b = color_b
                            got_color_g = color_g
                            got_color_r = color_r
                            got_color_str = color_str
                            best_pic_idx = pic_idx             # best_pic_idx 设定为此截图的idx
                            print('idx %d: color not valid ok, but has color, assume it as the pickup idx' % best_pic_idx)

                    if score_ok_flag == True:
                        continue

                    # 从百度api查找截图是否包含人脸库中数据
                    print('22222222222222222222222222222222222222222222222222222')
                    user_list = search_face(baidu_client, groupId, pic_file_name)

                    for user in user_list:  # 如果匹配到百度
                        print('333333333333333333333333333333333333333333333333333333333')
                        user_id = int(user['user_id'])
                        score = float(user['score'])
                        print('get user_face %d from pic %s, score %f' % (user_id, pic_file_name, score))
                        r.hset(people_info_str, 'score', score)  # 更新上传缓存中的百度匹配分数
                        for face_info in face_infos:
                            if face_info['userId'] == user_id and score >= BAIDU_APP_FACE_SCORE_MAX:
                                face_info['matchFaceCount'] = face_info['matchFaceCount'] + 1
                                update_pic_idx_flag = False
                                if face_info['maxFaceScore'] < score:
                                    face_info['maxFaceScore'] = score
                                    update_pic_idx_flag = True
                                if max_face_match_count < face_info['matchFaceCount']:
                                    max_face_match_count = face_info['matchFaceCount']
                                    max_face_match_score = face_info['maxFaceScore']
                                    if update_pic_idx_flag:
                                        max_face_match_idx = pic_idx
                                    qualifiedUser = user_id
                                    faceQualified = 1
                                if score >= BAIDU_APP_FACE_SCORE_OK:
                                    score_ok_flag = True
                                    print('score_ok %f, user id %d!, need no more detect face.' %
                                          (max_face_match_score, qualifiedUser))
                                    break
                else:
                    continue
            if max_face_match_idx >= 0:
                r.hmset(people_info_str, {'status': 1, 'score': max_face_match_score})
                best_pic_idx = max_face_match_idx
                print('44444444444444444444444444444444444444444444444444444444444444444444444')
                print('select best_pic_idx %d: max_face_match_count %d, userId %d, score %f' %
                      (best_pic_idx, max_face_match_count, qualifiedUser, max_face_match_score))
            else:
                print('5555555555555555555555555555555555555555555555555')
                r.hmset(people_info_str, {'status': 1, 'score': max_face_match_score})
                print('select best_pic_idx %d: no face matched' % (best_pic_idx))
            print('666666666666666666666666666666666666666666666666666')
            print('faceQualified %d, qualifiedUser %d, changingQualified %d\n' %
                  (faceQualified, qualifiedUser, changingQualified))

            for pic_idx in range(people_detect_count):        # 遍历截图
                people_info_str = PEOPLE_INFO_PREFIX + people_str + ':' + str(pic_idx)         # redis key, hmset
                score = r.hget(people_info_str, 'score').decode('utf-8')
                sequence = r.hget(people_info_str, 'sequence').decode('utf-8')
                status = r.hget(people_info_str, 'status').decode('utf-8')
                got_color_str = r.hget(people_info_str, 'color_str').decode('utf-8')  # 获取识别的衣服颜色
                got_color_b = r.hget(people_info_str, 'color_b').decode('utf-8')  # 获取识别的衣服颜色, BGR值
                got_color_g = r.hget(people_info_str, 'color_g').decode('utf-8')
                got_color_r = r.hget(people_info_str, 'color_r').decode('utf-8')
                face_x = r.hget(people_info_str, 'face_x').decode('utf-8')  # 获取人脸位置
                face_y = r.hget(people_info_str, 'face_y').decode('utf-8')
                face_w = r.hget(people_info_str, 'face_w').decode('utf-8')
                face_h = r.hget(people_info_str, 'face_h').decode('utf-8')
                body_x = r.hget(people_info_str, 'body_x').decode('utf-8')  # 获取人行位置
                body_y = r.hget(people_info_str, 'body_y').decode('utf-8')
                body_w = r.hget(people_info_str, 'body_w').decode('utf-8')
                body_h = r.hget(people_info_str, 'body_h').decode('utf-8')
                suit_x = r.hget(people_info_str, 'suit_x').decode('utf-8')  # 获取衣服位置
                suit_y = r.hget(people_info_str, 'suit_y').decode('utf-8')
                suit_w = r.hget(people_info_str, 'suit_w').decode('utf-8')
                suit_h = r.hget(people_info_str, 'suit_h').decode('utf-8')

                # upload info 上传最佳截图
                best_people_info_str = PEOPLE_INFO_PREFIX + people_str + ':' + str(pic_idx)
                best_pic_file_name = r.hget(best_people_info_str, 'pic').decode('utf-8')
                print('77777777777777777777777777777777777777777')
                ret = upload_info_to_server(UPLOAD_INFO_PREFIX, UPLOAD_FILE_PREFIX, DEV_NO, token, people_str,
                                            best_pic_file_name, faceQualified, qualifiedUser, changingQualified, score,
                                            got_color_b, got_color_g, got_color_r, got_color_str,
                                            face_x, face_y, face_w, face_h, body_x, body_y, body_w, body_h,
                                            suit_x, suit_y, suit_w, suit_h, status, sequence)
                print('--------------------------------------------------------------')
                print(UPLOAD_INFO_PREFIX, UPLOAD_FILE_PREFIX, DEV_NO, token, people_str, best_pic_file_name,
                      faceQualified,
                      qualifiedUser, changingQualified, score,
                      got_color_b, got_color_g, got_color_r, got_color_str, face_x, face_y, face_w, face_h,
                      body_x, body_y, body_w, body_h, suit_x, suit_y, suit_w, suit_h, status, sequence)
                print('--------------------------------------------------------------')
                if not ret:  # 重试获取token
                    token, start_color, end_color = get_token_from_server(DEVICE_INFO_PREFIX, DEV_NO, APP_ID,
                                                                          APP_SECRET)
                    print('888888888888888888888888888888888888888888888')
                    ret = upload_info_to_server(UPLOAD_INFO_PREFIX, UPLOAD_FILE_PREFIX, DEV_NO, token, people_str,
                                                best_pic_file_name, faceQualified, qualifiedUser, changingQualified,
                                                score,
                                                got_color_b, got_color_g, got_color_r, got_color_str,
                                                face_x, face_y, face_w, face_h, body_x, body_y, body_w, body_h,
                                                suit_x, suit_y, suit_w, suit_h, status, sequence)
                    if not ret:
                        print('999999999999999999999999999999999999999999999999')
                        print('upload_info_to_server error!, exit!')
                        exit(-1)

            # 从redis以及文件系统删除信息
            for idx in range(people_detect_count):
                people_info_str = PEOPLE_INFO_PREFIX + people_str + ':' + str(idx)
                pic_file_name = r.hget(people_info_str, 'pic').decode('utf-8')
                pic_face_file_name = r.hget(people_info_str, 'pic_face').decode('utf-8')
                try:
                    os.remove(pic_file_name)
                    # os.remove(pic_face_file_name)
                except Exception as e:
                    print('remove file error!')
                    print(e)
                finally:
                    pass
                r.delete(people_info_str)
            r.delete(people_detect_count_str)
            r.srem(PEOPLES_INDEX_SET_NAME, people)

        # 有新数据则马上循环,否则等待一秒
        if flags:
            time.sleep(0.1)
        else:
            time.sleep(1)

    print('end...')

exit(0)
