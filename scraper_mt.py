from threading import Thread, Lock 
import argparse

from time import sleep, time
from selenium import webdriver
from selenium.webdriver.common.by import By



start = time()

op = webdriver.ChromeOptions()
op.add_argument('--headless')
op.add_argument('--log-level=3')

parser = argparse.ArgumentParser()
parser.add_argument("--url", action="append", required=True)
parser.add_argument("--wn", type=int, default=16)
parser.add_argument("--pc", type=int, default=30)
args = vars(parser.parse_args())

links = [x for x in args["url"] if "vinted.it" in x]
workern = args["wn"]
pagec = args["pc"]

data = {}
queue = []
pageno = None
done = 0
dl = Lock()
ql = Lock()

def avg_price(user):
    return (sum([item[2] for item in user]) + 4)/len(user)
    

def scrape_page():
    global done
    page = None
    ql.acquire()
    if len(queue) == 0:
        ql.release()
        return
    else:
        page = queue.pop(0)
    ql.release()

    driver = webdriver.Chrome(options=op)

    driver.get(page)

    # country selection
    for _ in range(100):
        try:
            country = driver.find_element(By.CLASS_NAME, "web_ui__Modal__scrollable-content")
            country.find_element(By.XPATH, "./div/div/div/div[last()]/button").click()
            break
        except:
            continue

    sleep(1)

    # accept cookies
    for _ in range(100):
        try:
            driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
            break
        except:
            continue

    while True:
        grid = None
        for _ in range(10):
            try:
                grid = driver.find_elements(By.CLASS_NAME, "feed-grid")[0]
            except:
                sleep(.5)

        if grid == None:
            return
        
        items = grid.find_elements(By.CLASS_NAME, "new-item-box__container")
        for item in items:
            try:
                usr = item.find_element(By.XPATH, ".//a[@class='web_ui__Cell__cell web_ui__Cell__narrow web_ui__Cell__link'][1]").get_attribute("href")
                item_link = item.find_element(By.XPATH, ".//a[@class='new-item-box__overlay new-item-box__overlay--clickable'][1]").get_attribute("href")
                img = item.find_element(By.XPATH, ".//div[@class='web_ui__Image__image web_ui__Image__cover web_ui__Image__portrait web_ui__Image__scaled web_ui__Image__ratio'][1]/img[@class='web_ui__Image__content'][1]").get_attribute("src")
                price = float(item.find_element(By.XPATH, ".//p[@class='web_ui__Text__text web_ui__Text__subtitle web_ui__Text__left web_ui__Text__amplified web_ui__Text__bold'][1]").text.split(" ")[0].replace(",", "."))  
                
                dl.acquire()
                if usr not in data:
                    data[usr] = [(item_link, img, price)]
                else:
                    data[usr].append((item_link, img, price))
                dl.release()
            except Exception as e:
                continue

        ql.acquire()
        done += 1
        print(f"{done}/{pageno}")
        if len(queue) == 0:
            ql.release()
            return
        else:
            page = queue.pop(0)
        ql.release()

        driver.get(page)


for src in links:
    queue += [f"{src}&page={i}" for i in range(1, pagec)]
pageno = len(queue)

threads = []
for i in range(workern):
    threads.append(Thread(target=scrape_page, args=()))
    threads[-1].start()

for t in threads:
    t.join()

for usr in data:
    data[usr] = list(set(data[usr]))

data = dict(sorted(data.items(), key=lambda item: avg_price(item[1])/len(item[1])))


with open("output.html", "w") as f:
    f.write('<html> <body> <table>\n\n')
    for usr in data:
        f.write(f'<tr><h1>{usr} ({len(data[usr])}, avg: {round(avg_price(data[usr]), 2)})</h1>\n')
        for item in data[usr]:
            f.write(f'\t<a href={item[0]} target="_blank"><img src={item[1]}></a>\n')
        f.write("</tr> </br>\n\n")
    f.write("</table> </body></html>")

print(time() - start)