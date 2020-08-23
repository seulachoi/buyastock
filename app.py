from pymongo import MongoClient
from flask import Flask, request, render_template, jsonify
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
import krxlist
import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.dbsparta

stocklist=krxlist.stocklist    

# HTML 화면 보여주기
@app.route('/')
def home():
    return render_template('index.html')


# API 역할을 하는 부분
@app.route('/keywords', methods=['POST'])
def show_matched():
    #<검색한 키워드를 저장, counting 하기>
    # 1. 클라이언트가 전달한 keyword_give를 keyword_receive 변수에 넣습니다.
    keyword_receive = request.form['keyword_give']
    # 2. 새로운 키워드라면, mongoDB에 데이터 넣고, db keywords 목록에서 find_one으로 keyword가 keyword_receive와 일치하는 keyword를 찾습니다.
    keyword = db.db_keywords.find_one({'keyword': keyword_receive})
    if keyword is None:
        doc = {
            'keyword': keyword_receive,
            'count': 0
        }
        db.db_keywords.insert_one(doc)
        keyword = db.db_keywords.find_one({'keyword': keyword_receive})
    else:  # 3. 이미 있는 키워드라면, db keywords 목록에서 find_one으로 keyword가 keyword_receive와 일치하는 keyword를 찾습니다.
        keyword = db.db_keywords.find_one({'keyword': keyword_receive})

    # 4. keyword의 count 에 1을 더해준 new_like 변수를 만듭니다.
    new_count = keyword['count'] + 1
    # 4. keywords 목록에서 keyword가 keyword_receive인 문서의 count 를 new_count로 변경합니다.
    db.db_keywords.update_one({'keyword': keyword_receive}, {'$set': {'count': new_count}})
    # 참고: '$set' 활용하기!
    # 5. 성공하면 success 메시지를 반환합니다. (필요한가?, 없어야 하나?)
    #return jsonify({'result': 'success', 'msg': '성공!'})

    #<검색어를 셀레니움으로 검색하고, 검색 결과를 index1-2.html에 보여줌
    # 1. 클라이언트가 전달한 keyword_give를 keyword_receive 변수에 넣습니다
    keyword_receive = request.form['keyword_give']

    # 2. keyword_receive를 셀레니움으로 keyword를 검색합니다. 셀레니움 으로 키워드 크롤링해서 매칭 종목 찾기
    path = "C:/Users/sara/Desktop/chromedriver"
    driver = webdriver.Chrome(path)

    # rso > div:nth-child(3) > div > div.s > div > span #검색결과에서 보이는 본문만 가져오기
    # div > div.r > a > h3  #제목만

    ## 1.keyworkd 관련주 검색
    keyword = keyword_receive
    print(keyword)
    stock = '관련주'
    url = 'https://www.google.com/search?q=' + keyword + '+' + stock + '&aqs=chrome..69i57j69i61.1790j0j7&sourceid=chrome&ie=UTF-8'
    search_list = []

    driver.get(url)

    req = driver.page_source

    soup = BeautifulSoup(req, 'html.parser')
    news_divs = soup.select(
        '#rso> div.g')  # div중에서 class 'g' (div.g)인 것만 가져옴! 이미지가 중간에 나오는데, 이미지는 div class g가 아니어서 걸러짐

    for div in news_divs:
        head1 = div.select_one('div > div.s > div > span').text
        search_list.append(head1)

    ## 2.keyword 수혜주 검색
    keyword = keyword_receive
    stock = '수혜주'
    url = 'https://www.google.com/search?q=' + keyword + '+' + stock + '&aqs=chrome..69i57j69i61.1790j0j7&sourceid=chrome&ie=UTF-8'

    driver.get(url)

    req = driver.page_source

    soup = BeautifulSoup(req, 'html.parser')
    news_divs = soup.select('#rso> div.g')

    for div in news_divs:
        head2 = div.select_one('div > div.s > div > span').text
        search_list.append(head2)

    # rso > div:nth-child(1) > div > div.s > div > span
    # rso > div:nth-child(5) > div > div.s > div:nth-child(2) > span

    ## 3.주식 intitle: keyword 검색
    stock = '주식'
    keyword = keyword_receive
    url = 'https://www.google.com/search?q=' + stock + 'intitle:' + keyword + '&source=lnms&tbm=nws&sa=X&ved=2ahUKEwjR946125XrAhUSPXAKHeE9AnEQ_AUoAXoECA4QAw'

    driver.get(url)

    req = driver.page_source
    soup = BeautifulSoup(req, 'html.parser')
    news_divs = soup.select('#rso> div > g-card > div > div > div.dbsr > a > div')
    ##3-1
    for div in news_divs:
        head3_1 = div.select_one('div.JheGif.nDgy9d').text
        search_list.append(head3_1)

    ###셀레니움 2페이지 클릭하기 copy -> xpath 복사 후 driver.find_element_by_xpath 에 넣어주기
    element = driver.find_element_by_xpath("//*[@id='xjs']/div/table/tbody/tr/td[3]/a")
    element.click()

    req = driver.page_source
    soup = BeautifulSoup(req, 'html.parser')
    news_divs = soup.select('#rso> div > g-card > div > div > div.dbsr > a > div')
    ##3-2
    for div in news_divs:
        head3_2 = div.select_one('div.JheGif.nDgy9d').text
        search_list.append(head3_2)

    # head1,2,3-1,3-2에서 stocklist에 매칭되는 종목이 있는지 확인하고, 있으면 resultlist에 추가하기
    search_sentences = " ".join(search_list)
    search_words = search_sentences.split(" ")

    resultlist = []
    for data in stocklist:
        for word in search_words:
            if data in word:
                resultlist.append(data)

    # 여러 종목일 경우, 가장 많이 나온 5개를 출력하기
    print(resultlist)
    word_ranking = pd.Series(resultlist).value_counts()
    word_top5 = word_ranking[:5]
    list_number = len(resultlist)

    matched_list = []
    if list_number < 5:
        i=0
        while i < len(resultlist):
            matched_list.append(word_ranking.index[i])
            i+=1
    else:
        i=0
        while i <5 :
            matched_list.append(word_top5.index[i])
            i+=1
    print(matched_list)

    # 참고) star_list = list(db.mystar.find({},{'_id':False}).sort("like",-1))
    # 참고) find({},{'_id':False}), sort()를 활용하면 굿!

    # 2. 위 셀레니움 완료시, index1-2를 matched_list와 함께 보여줌
    return render_template('index1-2.html', data=matched_list, keyword_search = keyword_receive)

@app.route('/stocksinfo', methods=['GET'])
def stocks_info():
    matched_receive = request.args.get('title')
    print(matched_receive)

    # 종목 리서치 정보 가져오기
    path = "C:/Users/sara/Desktop/chromedriver"
    driver = webdriver.Chrome(path)

    a = datetime.datetime.today()
    edate = a.strftime("%Y-%m-%d")
    edt = datetime.datetime.now() - relativedelta(months=3)
    sdate = edt.strftime("%Y-%m-%d")

    stock = matched_receive
    stock_name = db.stocklist.find_one({'name': stock})
    stock_code = db.stocklist.find_one({'name': stock}, {'_id': False, 'name': False})
    code = stock_code['code']

    title_list = []
    url = 'http://consensus.hankyung.com/apps.analysis/analysis.list?sdate=' + sdate + '&edate=' + edate + '&now_page=1&search_value=&report_type=CO&pagenum=20&search_text=' + code + '&business_code='

    driver.get(url)

    req = driver.page_source

    soup = BeautifulSoup(req, 'html.parser')
    trs = soup.select('#contents > div.table_style01 > table > tbody > tr')

    for tr in trs:
        title = tr.select_one('td.text_l > div.layerPop > div > strong').text
        title_list.append(title)
    print(title_list)
    # contents > div.table_style01 > table > tbody > tr:nth-child(3) > td.text_l > a

    return render_template('index1-3.html', stockname=matched_receive, report=title_list)

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)