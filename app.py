from flask import Flask, render_template, request, jsonify
import os
import json
import re
import time
import io
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import networkx as nx
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from openai import OpenAI
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

# ================= KEYS =================
API_KEY = "ENTER YOUR API KEY"
OPENROUTER_API_KEY = "ENTER YOUR API KEY"
client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key="ENTER YOUR API KEY")


# ================= AI HELPERS =================
def generate_roadmap(topic):
    try:
        prompt = f"Create a 5-step learning roadmap for {topic}. Output ONLY HTML <li> tags. Example format: <li><strong>Step 1: Basics</strong> - Learn the fundamentals.</li>"
        res = client.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        return f'<ul class="timeline">{res.choices[0].message.content}</ul>'
    except:
        return '<ul class="timeline"><li><strong>Error:</strong> Roadmap generation delayed.</li></ul>'


def generate_learning_outcomes(description):
    try:
        res = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            data=json.dumps({"model": "openai/gpt-3.5-turbo", "messages": [{"role": "user",
                                                                            "content": f"Extract 2 short bullet points of what a student will learn. Return ONLY HTML <ul> and <li>: {description}"}]})
        )
        return res.json()["choices"][0]["message"]["content"]
    except:
        return "<ul><li>Summary not available.</li></ul>"


# ================= DATA CLEANING =================
def clean_enrollment(value):
    if pd.isna(value) or value == "N/A" or value == 0: return 0
    value = str(value).lower()
    match = re.search(r'([\d,.]+)\s*([mk]?)', value)
    if not match: return 0
    try:
        number = float(match.group(1).replace(",", ""))
        suffix = match.group(2)
        if suffix == 'm':
            number *= 1_000_000
        elif suffix == 'k':
            number *= 1_000
        return int(number)
    except:
        return 0


def fix_arabic(text):
    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return text


def get_course_data(url, driver):
    data = {"Title": "Unknown Course", "Instructor": "Coursera Instructor", "Enrollment": "0", "Rating": 0.0,
            "Reviews": 0, "Link": url}
    try:
        driver.get(url)
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        page_source = driver.page_source
        page_lower = page_source.lower()

        try:
            data["Title"] = driver.find_element(By.TAG_NAME, "h1").text.strip()
        except:
            pass

        try:
            texts = driver.find_elements(By.XPATH,
                                         "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'enrolled') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'learner')]")
            for t in texts:
                txt = t.text.strip()
                if txt and any(c.isdigit() for c in txt):
                    data["Enrollment"] = txt;
                    break
        except:
            pass

        try:
            instructors = driver.find_elements(By.CSS_SELECTOR,
                                               "a[href*='/instructor/'], span[data-e2e='instructorName']")
            if instructors: data["Instructor"] = instructors[0].text.strip()
        except:
            pass

        soup = BeautifulSoup(page_source, "lxml")

        def find_rating(obj):
            if isinstance(obj, dict):
                if 'aggregateRating' in obj and isinstance(obj['aggregateRating'], dict):
                    return obj['aggregateRating'].get('ratingValue'), obj['aggregateRating'].get('ratingCount')
                for v in obj.values():
                    res = find_rating(v)
                    if res != (None, None): return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_rating(item)
                    if res != (None, None): return res
            return None, None

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                js = json.loads(script.string)
                r_val, r_count = find_rating(js)
                if r_val: data["Rating"] = float(r_val)
                if r_count: data["Reviews"] = int(r_count)
            except:
                continue

        if data["Rating"] == 0.0:
            r_match = re.search(r'([\d\.]+)\s+out of 5 stars', page_lower)
            if r_match:
                data["Rating"] = float(r_match.group(1))
            else:
                rm = re.search(r'"ratingvalue"\s*:\s*"?([\d\.]+)"?', page_lower)
                if rm: data["Rating"] = float(rm.group(1))
    except:
        pass
    return data


def generate_plots(df_coursera, df_yt, yt_x_views, yt_y_likes, yt_labels, topic):
    plt.style.use('dark_background')
    plot_face_color = '#0b1121'
    os.makedirs('static/plots', exist_ok=True)

    if not df_coursera.empty and 'Enrollment_Clean' in df_coursera.columns:
        top_enroll = df_coursera.nlargest(10, "Enrollment_Clean")
        if not top_enroll.empty:
            plt.figure(figsize=(10, 6), facecolor=plot_face_color)
            ax = plt.axes()
            ax.set_facecolor(plot_face_color)
            titles_arabic = [fix_arabic(t[:30]) for t in top_enroll["Title"]]
            plt.barh(titles_arabic, top_enroll["Enrollment_Clean"], color='#0ea5e9')
            plt.title(fix_arabic(f"Top Courses by Enrollment"), color='white', fontweight='bold')
            plt.gca().invert_yaxis()
            ax.tick_params(colors='white')
            plt.xlabel("Total Enrollment", color='white')
            plt.savefig("static/plots/bar.png", facecolor=plot_face_color, bbox_inches='tight');
            plt.close()

    if not df_coursera.empty and 'Rating' in df_coursera.columns and 'Reviews' in df_coursera.columns:
        clean_df = df_coursera.dropna(subset=["Rating", "Reviews"]).copy()
        if len(clean_df) > 1:
            data_x = clean_df["Rating"];
            data_y = clean_df["Reviews"]
            data_x = (data_x - data_x.min()) / (data_x.max() - data_x.min() + 1e-9)
            data_y = (data_y - data_y.min()) / (data_y.max() - data_y.min() + 1e-9)
            R = 0.2

            def kde_distance_based(d, R):
                return np.exp(-(d ** 2) / (2 * (R / 2) ** 2))

            x_vals = np.linspace(0, 1, 100);
            y_vals = np.linspace(0, 1, 100)
            heatmap = np.zeros((len(y_vals), len(x_vals)))
            for i, xg in enumerate(x_vals):
                for j, yg in enumerate(y_vals):
                    dists = np.sqrt((xg - data_x.values) ** 2 + (yg - data_y.values) ** 2)
                    heatmap[j, i] = np.sum(kde_distance_based(dists, R))
            plt.figure(figsize=(8, 6), facecolor=plot_face_color)
            plt.imshow(heatmap, extent=(0, 1, 0, 1), origin="lower", cmap="hot")
            plt.colorbar(label="Density").ax.yaxis.label.set_color('white')
            plt.scatter(data_x, data_y, edgecolors="white", facecolors='none')
            plt.title("Heatmap (Rating vs Reviews)", color='white')
            plt.savefig("static/plots/heatmap.png", facecolor=plot_face_color, bbox_inches='tight');
            plt.close()

    if not df_coursera.empty and 'Enrollment_Clean' in df_coursera.columns:
        clean_3d = df_coursera.dropna(subset=["Rating", "Reviews", "Enrollment_Clean", "Title"]).copy()
        clean_3d = clean_3d[clean_3d["Rating"] > 0]
        if not clean_3d.empty:
            clean_3d["Reviews_log"] = np.log1p(clean_3d["Reviews"].astype(float))
            clean_3d["Enrollment_log"] = np.log1p(clean_3d["Enrollment_Clean"].astype(float))
            fig = plt.figure(figsize=(10, 8), facecolor=plot_face_color)
            ax = fig.add_subplot(projection='3d')
            ax.set_facecolor(plot_face_color)
            ax.xaxis.label.set_color('white');
            ax.yaxis.label.set_color('white');
            ax.zaxis.label.set_color('white')
            ax.tick_params(colors='white')
            scatter = ax.scatter(clean_3d["Rating"], clean_3d["Reviews_log"], clean_3d["Enrollment_log"],
                                 c=clean_3d["Enrollment_log"], cmap='viridis', s=80)
            ax.set_xlabel("Rating");
            ax.set_ylabel("Reviews (log)");
            ax.set_zlabel("Enrollment (log)")
            ax.view_init(elev=25, azim=45)
            cbar = fig.colorbar(scatter, ax=ax, label="Enrollment (log)")
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
            top_n = clean_3d.nlargest(10, "Enrollment_Clean")
            for i in top_n.index:
                ax.text(clean_3d.loc[i, "Rating"], clean_3d.loc[i, "Reviews_log"], clean_3d.loc[i, "Enrollment_log"],
                        fix_arabic(clean_3d.loc[i, "Title"][:20] + "..."), fontsize=8, color='white')
            plt.title("3D Plot: Coursera Courses", color='white')
            plt.savefig("static/plots/3d_coursera.png", facecolor=plot_face_color, bbox_inches='tight');
            plt.close()

    if len(yt_x_views) > 1:
        X_arr, Y_arr = np.array(yt_x_views), np.array(yt_y_likes)
        x_min, x_max = 0, max(X_arr.max() * 1.1, 1);
        y_min, y_max = 0, max(Y_arr.max() * 1.1, 1)
        XX, YY = np.meshgrid(np.linspace(x_min, x_max, 100), np.linspace(y_min, y_max, 100))
        sigma_x, sigma_y = max((x_max - x_min) * 0.1, 1), max((y_max - y_min) * 0.1, 1)
        yt_heatmap = sum(
            np.exp(-(((XX - px) / sigma_x) ** 2 + ((YY - py) / sigma_y) ** 2) / 2) for px, py in zip(X_arr, Y_arr))
        fig, ax = plt.subplots(figsize=(9, 6), facecolor=plot_face_color)
        im = ax.imshow(yt_heatmap, origin="lower", cmap="hot", aspect="auto", extent=[x_min, x_max, y_min, y_max])
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Density", color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        ax.set_title("Views vs Likes Heatmap — YouTube", color='white', fontweight="bold", pad=12)
        ax.set_xlabel("Views", color='white');
        ax.set_ylabel("Likes", color='white')
        ax.tick_params(colors='white')
        plt.savefig("static/plots/youtube_heatmap.png", facecolor=plot_face_color, bbox_inches='tight');
        plt.close()

    if not df_yt.empty:
        G = nx.DiGraph()
        topic_disp = fix_arabic(topic)
        G.add_node(topic_disp, type="topic")
        for _, row in df_yt.iterrows():
            channel = fix_arabic(row.get("channel", "Unknown"))
            vid_title = fix_arabic(row.get("title", "Video")[:20] + "...")
            G.add_node(channel, type="channel");
            G.add_edge(topic_disp, channel)
            G.add_node(vid_title, type="video");
            G.add_edge(channel, vid_title)
        color_map = ["#0ea5e9" if G.nodes[n].get("type") == "topic" else "#8b5cf6" if G.nodes[n].get(
            "type") == "channel" else "#f43f5e" for n in G.nodes()]
        plt.figure(figsize=(10, 8), facecolor=plot_face_color)
        nx.draw(G, nx.spring_layout(G, seed=42), with_labels=True, node_color=color_map, node_size=1500, font_size=10,
                font_color='white', font_weight="bold", edge_color="gray")
        plt.title("Network Graph: Relationships", color='white')
        plt.savefig("static/plots/network.png", facecolor=plot_face_color, bbox_inches='tight');
        plt.close()

    if len(yt_x_views) > 1:
        X_log = np.log10(np.array(yt_x_views) + 1);
        Y_log = np.log10(np.array(yt_y_likes) + 1)
        Z_idx = np.arange(1, len(yt_x_views) + 1)
        fig = plt.figure(figsize=(10, 8), facecolor=plot_face_color)
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor(plot_face_color)
        ax.xaxis.label.set_color('white');
        ax.yaxis.label.set_color('white');
        ax.zaxis.label.set_color('white')
        ax.tick_params(colors='white')
        scatter = ax.scatter(X_log, Y_log, Z_idx, c=Z_idx, cmap='viridis', s=120, alpha=0.9)

        for i in range(len(X_log)):
            ax.text(X_log[i], Y_log[i], Z_idx[i], fix_arabic(yt_labels[i]), fontsize=8, color='white')

        centroid_x, centroid_y, centroid_z = np.mean(X_log), np.mean(Y_log), np.mean(Z_idx)
        ax.scatter(centroid_x, centroid_y, centroid_z, c='red', s=180, marker='o')
        ax.text(centroid_x, centroid_y, centroid_z + 0.5, "Centroid", color='red', fontweight='bold')
        ax.set_xlabel("Views (log)");
        ax.set_ylabel("Likes (log)");
        ax.set_zlabel("Video Index")
        ax.set_title(f"3D Point Cloud", color='white', fontweight='bold', pad=20)
        ax.view_init(elev=30, azim=10)
        cbar = plt.colorbar(scatter, pad=0.1)
        cbar.set_label("Video Index", color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        plt.savefig("static/plots/3d_youtube.png", facecolor=plot_face_color, bbox_inches='tight');
        plt.close()


# ================= ROUTES =================
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"})

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"})

    try:
        file_bytes = file.read()
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding='cp1256')
            except:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding='latin1')

        topic = "Imported CSV Data"
        roadmap = "<ul class='timeline'><li><strong>Step 1: Data Loaded</strong> - CSV File successfully parsed.</li><li><strong>Step 2: Processing</strong> - Data mapped to visual analytics.</li></ul>"
        all_courses = []
        rows_coursera = []
        yt_data = []
        yt_x_views, yt_y_likes, yt_labels = [], [], []

        for _, row in df.iterrows():
            row_dict = {str(k).lower(): v for k, v in row.items()}
            title = str(row_dict.get('title', 'Unknown Course'))
            link = str(row_dict.get('link', row_dict.get('href', '#')))

            platform = "COURSERA"
            if 'youtube' in link.lower() or 'views' in row_dict or 'channel' in row_dict:
                platform = "YOUTUBE"
            if 'platform' in row_dict:
                platform = str(row_dict['platform']).upper()

            if platform == "COURSERA":
                enr = row_dict.get('enrollment', row_dict.get('enrollment_clean', 0))
                clean_enr = clean_enrollment(enr)
                rating = float(row_dict.get('rating', 0.0))
                reviews = int(float(row_dict.get('reviews', 0)))
                instructor = str(row_dict.get('instructor', 'Unknown'))

                rows_coursera.append(
                    {"Title": title, "Instructor": instructor, "Enrollment_Clean": clean_enr, "Rating": rating,
                     "Reviews": reviews, "Link": link})

                all_courses.append({
                    "platform": "COURSERA", "title": title, "instructor": instructor,
                    "metrics": f"{clean_enr:,} Enrolled" if clean_enr else "N/A", "likes": "N/A",
                    "rating": str(rating), "link": link,
                    "score": rating * np.log1p(clean_enr) if rating > 0 else 0,
                    "badge_color": "blue", "price": "CSV",
                    "summary": "<ul><li>Imported efficiently from CSV dataset</li></ul>"
                })
            else:
                views = row_dict.get('views', row_dict.get('metrics', 0))
                clean_v = clean_enrollment(views)
                likes = row_dict.get('likes', 0)
                clean_l = clean_enrollment(likes) if likes else 1
                channel = str(row_dict.get('channel', row_dict.get('instructor', 'Unknown')))

                yt_data.append({"title": title, "channel": channel, "views": str(views), "href": link})
                yt_x_views.append(clean_v);
                yt_y_likes.append(clean_l);
                yt_labels.append(title[:20])

                all_courses.append({
                    "platform": "YOUTUBE", "title": title, "instructor": channel,
                    "metrics": str(views), "likes": str(likes), "rating": "YouTube", "link": link,
                    "score": 5.0 * np.log1p(clean_v), "badge_color": "red", "price": "CSV",
                    "summary": "<ul><li>Imported efficiently from CSV dataset</li></ul>"
                })

        df_coursera = pd.DataFrame(rows_coursera)
        df_yt = pd.DataFrame(yt_data)

        generate_plots(df_coursera, df_yt, yt_x_views, yt_y_likes, yt_labels, topic)

        all_courses = sorted(all_courses, key=lambda x: x['score'], reverse=True)
        recommended_courses = all_courses[:3]
        other_courses = all_courses[3:]

        return jsonify(
            {"status": "success", "roadmap": roadmap, "recommended": recommended_courses, "all_courses": other_courses})

    except Exception as e:
        return jsonify({"status": "error", "message": f"CSV Parsing Error: {str(e)}"})


@app.route('/run_scraper', methods=['POST'])
def run_scraper():
    topic = request.get_json().get('topic')
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        roadmap = generate_roadmap(topic)
        all_courses = []
        rows_coursera = []

        params = {"engine": "google", "q": f"site:coursera.org {topic} course", "api_key": API_KEY}
        results = GoogleSearch(params).get_dict()
        if "organic_results" in results:
            count = 0
            for item in results["organic_results"]:
                url = item.get("link", "")
                if "/articles/" in url or "/collections/" in url or "/business/" in url: continue
                if "/learn/" in url or "/specializations/" in url or "/professional-certificates/" in url:
                    if count >= 15: break
                    c_data = get_course_data(url, driver)
                    if c_data["Title"] != "Unknown Course":
                        rows_coursera.append(c_data)
                        clean_enr = clean_enrollment(c_data["Enrollment"])
                        c_data["Enrollment_Clean"] = clean_enr
                        all_courses.append({
                            "platform": "COURSERA", "title": c_data["Title"], "instructor": c_data["Instructor"],
                            "metrics": f"{clean_enr:,} Enrolled" if clean_enr else "N/A", "likes": "N/A",
                            "rating": str(c_data["Rating"]), "link": url,
                            "score": c_data["Rating"] * np.log1p(clean_enr) if c_data["Rating"] > 0 else 0,
                            "badge_color": "blue", "price": "Certificate",
                            "summary": "<ul><li>Official Certification</li><li>Comprehensive Curriculum</li></ul>"
                        })
                        count += 1

        df_coursera = pd.DataFrame(rows_coursera)

        driver.get("https://www.youtube.com/results?search_query=" + topic + " full course")
        time.sleep(3)
        videos = driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")[:8]
        yt_data = []
        for v in videos:
            try:
                title_elem = v.find_element(By.CSS_SELECTOR, "a#video-title")
                title = title_elem.get_attribute("title")
                href = title_elem.get_attribute("href")
                channel = v.find_element(By.CSS_SELECTOR, ".long-byline a").text
                views = v.find_element(By.CSS_SELECTOR, "span.inline-metadata-item").text
                yt_data.append({"title": title, "href": href, "channel": channel, "views": views})
            except:
                continue

        yt_x_views, yt_y_likes, yt_labels = [], [], []

        for yt in yt_data:
            driver.get(yt["href"]);
            time.sleep(2)
            try:
                likes = re.search(r"[\d,]+",
                                  driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="like"]').get_attribute(
                                      "aria-label")).group(0)
            except:
                likes = "0"
            try:
                desc = driver.find_element(By.CSS_SELECTOR, "#description-inline-expander").text[:350]
            except:
                desc = ""

            clean_v = clean_enrollment(yt["views"])
            clean_l = float(likes.replace(",", "")) if any(c.isdigit() for c in likes) else 1
            yt_x_views.append(clean_v)
            yt_y_likes.append(clean_l)
            yt_labels.append(yt["title"][:20])

            outcomes = generate_learning_outcomes(desc) if desc else "<ul><li>Summary not available.</li></ul>"

            all_courses.append({
                "platform": "YOUTUBE", "title": yt["title"], "instructor": yt["channel"],
                "metrics": yt["views"], "likes": likes, "rating": "YouTube", "link": yt["href"],
                "score": 5.0 * np.log1p(clean_v), "badge_color": "red", "price": "FREE", "summary": outcomes
            })

        df_yt = pd.DataFrame(yt_data)
        driver.quit()

        generate_plots(df_coursera, df_yt, yt_x_views, yt_y_likes, yt_labels, topic)

        all_courses = sorted(all_courses, key=lambda x: x['score'], reverse=True)
        recommended_courses = all_courses[:3]
        other_courses = all_courses[3:]

        return jsonify(
            {"status": "success", "roadmap": roadmap, "recommended": recommended_courses, "all_courses": other_courses})

    except Exception as e:
        if 'driver' in locals(): driver.quit()
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    app.run(debug=True)