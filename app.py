import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, render_template, request, session
from flask_session import Session

app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = "filesystem"
app.debug = True
Session(app)

df = None
cos_sim = None

def process_csv(csv, seperator=','):
    print('Loading data...')
    df = pd.read_csv(csv, sep=seperator, on_bad_lines='skip')
    df = df.head(20000)

    df = df.dropna(how='any')
    df = df.drop_duplicates(subset='title', keep='first')
    # df.head(5)
    return df

def get_cos_sim(df):
    combined = df[df.columns[2:-1]].apply(
        lambda x: ','.join(x.dropna().astype(str)),
        axis=1
    ).str.lower().replace({"[^A-Za-z0-9 ]+": ""}, regex=True)
    combined = combined.reset_index(drop=True)
    # combined.head()

    #################################
    #################################

    count = CountVectorizer(stop_words='english')
    count_matrix = count.fit_transform(combined)

    #     tfidf = TfidfVectorizer(stop_words='english')
    #     tfidf_matrix = tfidf.fit_transform(data_plot['subtopics'])

    #     combine_sparse = sp.hstack([count_matrix, tfidf_matrix], format='csr')

    count2 = CountVectorizer(stop_words='english')
    count_matrix2 = count2.fit_transform(df[df.columns[-1]].apply(lambda x: x[1:-1].replace(',', ' ')))
    combine_sparse = sp.hstack([count_matrix, count_matrix2], format='csr')

    cos_sim = cosine_similarity(combine_sparse, combine_sparse)

    print('Loaded data.')
    return cos_sim

def recommend(title, df, cos_sim):
    indices = pd.Series(df.index, index = df['title'])
    index = indices[title]
    print(index)

    sim_scores = list(enumerate(cos_sim[index]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:10]

    indices = [i[0] for i in sim_scores]
    return indices

df = process_csv('./items20000.csv')
cos_sim = get_cos_sim(df)
indices = recommend('Red Queen 1', df, cos_sim)
print(df.iloc[indices])

@app.route('/')
def home():
    return "HOME"

if __name__ == '__main__':
    app.run()
