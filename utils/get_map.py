import math
from math import floor, pi, log, tan, atan, exp
from threading import Thread, Lock
import urllib.request as ur
import PIL.Image as pil
import io

MAP_URLS = {
    "google": "https://mt.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&hl=en",
    "amap": "http://wprd02.is.autonavi.com/appmaptile?style={style}&x={x}&y={y}&z={z}",
    "tencent_s": "http://p3.map.gtimg.com/sateTiles/{z}/{fx}/{fy}/{x}_{y}.jpg",
    "tencent_m": "http://rt0.map.gtimg.com/tile?z={z}&x={x}&y={y}&styleid=3",
    "tianditu": "http://t0.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=44518022c830cd5b51a7356926ede1a4",
    "usda": "https://gis.apfo.usda.gov/arcgis/rest/services/NAIP/USDA_CONUS_PRIME/ImageServer/tile/{z}/{y}/{x}",
    'arcgisonline': 'https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
}

COUNT = 0
mutex = Lock()

def transformLat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def transformLon(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def delta(lat, lon):
    a = 6378245.0
    ee = 0.00669342162296594323
    dLat = transformLat(lon - 105.0, lat - 35.0)
    dLon = transformLon(lon - 105.0, lat - 35.0)
    radLat = lat / 180.0 * math.pi
    magic = math.sin(radLat)
    magic = 1 - ee * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * math.pi)
    dLon = (dLon * 180.0) / (a / sqrtMagic * math.cos(radLat) * math.pi)
    return {'lat': dLat, 'lon': dLon}


def outOfChina(lat, lon):
    # if (lon < 72.004 or lon > 137.8347):
    #     return True
    # if (lat < 0.8293 or lat > 55.8271):
    #     return True
    return False


def gcj_to_wgs(gcjLon, gcjLat):
    if outOfChina(gcjLat, gcjLon):
        return (gcjLon, gcjLat)
    d = delta(gcjLat, gcjLon)
    return (gcjLon - d["lon"], gcjLat - d["lat"])


def wgs_to_gcj(wgsLon, wgsLat):
    if outOfChina(wgsLat, wgsLon):
        return wgsLon, wgsLat
    d = delta(wgsLat, wgsLon);
    return wgsLon + d["lon"], wgsLat + d["lat"]


def wgs_to_macator(x, y):
    y = 85.0511287798 if y > 85.0511287798 else y
    y = -85.0511287798 if y < -85.0511287798 else y

    x2 = x * 20037508.34 / 180
    y2 = log(tan((90 + y) * pi / 360)) / (pi / 180)
    y2 = y2 * 20037508.34 / 180
    return x2, y2

def mecator_to_wgs(x, y):
    x2 = x / 20037508.34 * 180
    y2 = y / 20037508.34 * 180
    y2 = 180 / pi * (2 * atan(exp(y2 * pi / 180)) - pi / 2)
    return x2, y2

def wgs84_to_tile(j, w, z, source):
    '''
    Get google-style tile cooridinate from geographical coordinate
    j : Longittude
    w : Latitude
    z : zoom
    '''
    if source not in ['google', 'tianditu', 'arcgisonline']:
        j, w = wgs_to_gcj(j, w)
    isnum = lambda x: isinstance(x, int) or isinstance(x, float)
    if not (isnum(j) and isnum(w)):
        raise TypeError("j and w must be int or float!")

    if not isinstance(z, int) or z < 0 or z > 22:
        raise TypeError("z must be int and between 0 to 22.")

    if j < 0:
        j = 180 + j
    else:
        j += 180
    j /= 360  # make j to (0,1)

    w = 85.0511287798 if w > 85.0511287798 else w
    w = -85.0511287798 if w < -85.0511287798 else w
    w = log(tan((90 + w) * pi / 360)) / (pi / 180)
    w /= 180  # make w to (-1,1)
    w = 1 - (w + 1) / 2  # make w to (0,1) and left top is 0-point

    num = 2 ** z
    x = floor(j * num)
    y = floor(w * num)
    return x, y


def tileframe_to_mecatorframe(zb):
    inx, iny = zb["LT"]  # left top
    inx2, iny2 = zb["RB"]  # right bottom
    length = 20037508.3427892
    sum = 2 ** zb["z"]
    LTx = inx / sum * length * 2 - length
    LTy = -(iny / sum * length * 2) + length

    RBx = (inx2 + 1) / sum * length * 2 - length
    RBy = -((iny2 + 1) / sum * length * 2) + length

    res = {'LT': (LTx, LTy), 'RB': (RBx, RBy),
           'LB': (LTx, RBy), 'RT': (RBx, LTy)}
    return res


def tileframe_to_pixframe(zb):
    out = {}
    width = (zb["RT"][0] - zb["LT"][0] + 1) * 256
    height = (zb["LB"][1] - zb["LT"][1] + 1) * 256
    out["LT"] = (0, 0)
    out["RT"] = (width, 0)
    out["LB"] = (0, -height)
    out["RB"] = (width, -height)
    return out

class Downloader(Thread):
    def __init__(self, index, count, urls, datas, update):
        super().__init__()
        self.urls = urls
        self.datas = datas
        self.index = index
        self.count = count
        self.update = update

    def download(self, url):
        HEADERS = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0",
        }
        header = ur.Request(url, headers=HEADERS)
        err = 0
        while (err < 3):
            try:
                data = ur.urlopen(header).read()
            except:
                err += 1
            else:
                return data
        raise Exception("Bad network link.")

    def run(self):
        for i, url in enumerate(self.urls):
            if i % self.count != self.index:
                continue
            self.datas[i] = self.download(url)
            if mutex.acquire():
                self.update()
                mutex.release()


def geturl(source, x, y, z, style):
    '''
    Get the picture's url for download.
    style:
        m for map
        s for satellite
    source:
        google or amap or tencent
    x y:
        google-style tile coordinate system
    z:
        zoom
    '''
    if source == 'google':
        furl = MAP_URLS["google"].format(x=x, y=y, z=z, style=style)
    elif source == 'amap':
        # for amap 6 is satellite and 7 is map.
        style = 6 if style == 's' else 7
        furl = MAP_URLS["amap"].format(x=x, y=y, z=z, style=style)
    elif source == 'usda':
        furl = MAP_URLS["usda"].format(x=x, y=y, z=z, style=style)
        pass
    elif source == 'arcgisonline':
        furl = MAP_URLS["arcgisonline"].format(x=x, y=y, z=z, style=style)
    elif source == 'tianditu':
        furl = MAP_URLS["tianditu"].format(x=x, y=y, z=z, style=style)
        pass
    elif source == 'tencent':
        y = 2 ** z - 1 - y
        if style == 's':
            furl = MAP_URLS["tencent_s"].format(
                x=x, y=y, z=z, fx=floor(x / 16), fy=floor(y / 16))
        else:
            furl = MAP_URLS["tencent_m"].format(x=x, y=y, z=z)
    else:
        raise Exception("Unknown Map Source ! ")

    return furl


def downpics(urls, multi=10):
    def makeupdate(s):
        def up():
            global COUNT
            COUNT += 1
            print("\b" * 45, end='')
            print("DownLoading ... [{0}/{1}]".format(COUNT, s), end='')

        return up

    url_len = len(urls)
    datas = [None] * url_len
    if multi < 1 or multi > 20 or not isinstance(multi, int):
        raise Exception("multi of Downloader shuold be int and between 1 to 20.")
    tasks = [Downloader(i, multi, urls, datas, makeupdate(url_len)) for i in range(multi)]
    for i in tasks:
        i.start()
    for i in tasks:
        i.join()

    return datas


def getpic(x1, y1, x2, y2, z, source='google', outfile="MAP_OUT.png", style='s'):
    pos1x, pos1y = wgs84_to_tile(x1, y1, z, source)
    pos2x, pos2y = wgs84_to_tile(x2, y2, z, source)
    lenx = pos2x - pos1x + 1
    leny = pos2y - pos1y + 1

    urls = [geturl(source, i, j, z, style,) for j in range(pos1y, pos1y + leny) for i in range(pos1x, pos1x + lenx)]

    datas = downpics(urls)

    outpic = pil.new('RGBA', (lenx * 256, leny * 256))
    for i, data in enumerate(datas):
        picio = io.BytesIO(data)
        small_pic = pil.open(picio)

        y, x = i // lenx, i % lenx
        outpic.paste(small_pic, (x * 256, y * 256))

    if outfile.lower().endswith('.jpg') or outfile.lower().endswith('.jpeg'):
        outpic = outpic.convert("RGB")  # 转换为RGB模式
    outpic = outpic.resize((1024, 1024))
    outpic.save(outfile)
    return {"LT": (pos1x, pos1y), "RT": (pos2x, pos1y), "LB": (pos1x, pos2y), "RB": (pos2x, pos2y), "z": z}


def screen_out(zb, name):
    if not zb:
        print("N/A")
        return
    print("坐标形式：", name)
    print("左上：({0:.5f},{1:.5f})".format(*zb['LT']))
    print("右上：({0:.5f},{1:.5f})".format(*zb['RT']))
    print("左下：({0:.5f},{1:.5f})".format(*zb['LB']))
    print("右下：({0:.5f},{1:.5f})".format(*zb['RB']))


# 地球半径，单位为米
R = 6378137


# 经纬度到弧度的转换
def deg_to_rad(degrees):
    return degrees * math.pi / 180


# 弧度到经纬度的转换
def rad_to_deg(radians):
    return radians * 180 / math.pi


# 计算经度变化
def calculate_new_longitude(lon, lat, distance=111):
    # 纬度转换为弧度
    lat_rad = deg_to_rad(lat)

    # 计算经度的弧度变化
    delta_lon_rad = distance / (R * math.cos(lat_rad))

    # 计算新的经度
    new_lon = lon + rad_to_deg(delta_lon_rad)

    return new_lon

if __name__ == '__main__':
    for source in ['arcgisonline', 'google', 'usda']:
        x = getpic(120.660, 24.157, calculate_new_longitude(120.660,24.153), 24.153,
               18, source=source, style='s', outfile="{}.jpg".format(source))
