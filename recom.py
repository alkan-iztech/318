import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def process_csv(csv, seperator=','):
    print('Loading df...')
    df = pd.read_csv(csv, sep=seperator, on_bad_lines='skip')
    df = df.dropna(how='any')
    # df = df.drop_duplicates(subset='title', keep='first')
    print('...loaded df.')
    return df

def get_combined(df):
    combined = df[df.columns[1:-1]].apply(
        lambda x: ','.join(x.dropna().astype(str)),
        axis=1
    ).str.lower().replace({"[^A-Za-z0-9 ]+": ""}, regex=True)
    combined = combined.reset_index(drop=True)
    # combined.head()
    return combined

def get_cos_sim(df, combined):
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

def recommend(row, num_of_recs=5):
    sim_scores = list(enumerate(row))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:num_of_recs+1]

    indices = [i[0] for i in sim_scores]
    return indices
