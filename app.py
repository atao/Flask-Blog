# https://python.developpez.com/tutoriel/intro-flask-python3/

import sqlite3
import markdown
import bleach
from waitress import serve
from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post


def clean_html(content):
    """
    Nettoie le contenu HTML pour éviter les attaques XSS.
    """
    allowed_tags = list(bleach.sanitizer.ALLOWED_TAGS) + ['p', 'h1', 'h2', 'h3', 'strong', 'em', 'ul', 'ol', 'li', 'a']
    allowed_attributes = {'a': ['href', 'title']}
    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'


@app.route('/', methods=('GET', 'POST'))
def index():
    conn = get_db_connection()
    if request.method == "POST":
        data = dict(request.form)
        search_string = data["search"]
        posts = conn.execute('SELECT * FROM posts WHERE title LIKE ? ', ("%" + search_string + "%",)).fetchall()
        if not posts:
            flash('No results for "{}"'.format(data["search"]))
    else:
        search_string = ""
        posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    return render_template('index.html', posts=posts, search_string=search_string)


@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    post = dict(post)
    # Rendre le Markdown
    raw_html = markdown.markdown(post['content'], extensions=['extra'])
    # Nettoyer le HTML avec la fonction clean_html
    post['content'] = clean_html(raw_html)
    return render_template('post.html', post=post)


@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            # Nettoyer le contenu avec la fonction clean_html
            cleaned_content = clean_html(content)

            conn = get_db_connection()
            conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, cleaned_content))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('create.html')


@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            # Nettoyer le contenu avec bleach
            cleaned_content = clean_html(content)

            conn = get_db_connection()
            conn.execute('UPDATE posts SET title = ?, content = ?'
                         ' WHERE id = ?',
                         (title, cleaned_content, id))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)


@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post['title']))
    return redirect(url_for('index'))


mode="dev"

if __name__ == '__main__':
    if mode == "dev":
        app.run(debug=True, port=8080)
    else:
        serve(app, host='0.0.0.0', port=8080, threads=4, url_prefix="/app")
