# 🎓 EduSearch Analyzer

**AI-Powered Educational Data Acquisition & Analytics Platform**

EduSearch Analyzer is a full-stack web application that scrapes, analyzes, and visualizes online course data from **YouTube** and **Coursera** — helping learners make data-driven decisions about their education.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?logo=flask)
![Selenium](https://img.shields.io/badge/Selenium-WebDriver-43B02A?logo=selenium)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## ✨ Features

- **Live Web Scraping** — Automated data collection from Coursera and YouTube using Selenium & BeautifulSoup
- **AI-Powered Roadmaps** — Generates personalized learning paths using LLM APIs
- **Smart Recommendations** — Ranks courses by a composite score (rating × log enrollment)
- **Advanced Visualizations** — KDE heatmaps, 3D scatter plots, network graphs (NetworkX + Matplotlib)
- **CSV Import** — Upload your own dataset for instant analysis
- **Built-in Presentation** — 15-slide interactive deck explaining the project methodology
- **Arabic Language Support** — Proper RTL text rendering with `arabic-reshaper` and `python-bidi`

---

## 📸 Screenshots

| Dashboard | Visual Analytics | Presentation Mode |
|-----------|-----------------|-------------------|
| ![dashboard](docs/screenshots/dashboard.png) | ![plots](docs/screenshots/plots.png) | ![presentation](docs/screenshots/presentation.png) |

> Add your own screenshots in `docs/screenshots/`

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python, Flask |
| **Scraping** | Selenium, BeautifulSoup, SerpAPI |
| **Data Processing** | Pandas, NumPy |
| **Visualization** | Matplotlib, NetworkX |
| **AI/LLM** | OpenRouter API (LLaMA 3, GPT-3.5) |
| **Frontend** | HTML5, CSS3, JavaScript |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Google Chrome (for Selenium)
- API keys for SerpAPI and OpenRouter

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/edusearch-analyzer.git
cd edusearch-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Configuration

Create a `.env` file in the project root:

```env
SERPAPI_KEY=your_serpapi_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
```

### Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📁 Project Structure

```
edusearch-analyzer/
├── app.py                 # Flask app + scraping + plotting logic
├── requirements.txt       # Python dependencies
├── .env.example           # Template for environment variables
├── .gitignore
├── templates/
│   └── index.html         # Main dashboard UI
├── static/
│   ├── style.css          # Global styles
│   └── plots/             # Generated plot images
└── docs/
    └── screenshots/       # Project screenshots
```

---

## 📊 Visualizations

The platform generates 6 types of plots:

1. **Bar Chart** — Top courses by enrollment count
2. **KDE Heatmap** — Rating vs. Reviews density distribution
3. **3D Scatter (Coursera)** — Rating × Reviews × Enrollment
4. **YouTube Heatmap** — Views vs. Likes density
5. **Network Graph** — Topic → Channel → Video relationships
6. **3D Point Cloud (YouTube)** — Views × Likes × Video index with centroid

---

## 🔮 Future Roadmap

- [ ] Expand to Udemy, edX, Khan Academy
- [ ] ML-based personalized recommendations
- [ ] Real-time price tracking & alerts
- [ ] Mobile app
- [ ] NLP sentiment analysis on course reviews

---

## 📄 License

This project is proprietary software. All rights reserved.
Unauthorized use, copying, or distribution is strictly prohibited.

---

## 👤 Authors

**Yousef Mostafa & Omar Elrawy**
- LinkedIn: Yousef Mostafa (www.linkedin.com/in/yousef-mostafa-a61950263)
- GitHub: yousefmostafa16(https://github.com/yousefmostafa16)
