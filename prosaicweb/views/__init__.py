# prosaicweb
# Copyright (C) 2016  nathaniel smith
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from io import StringIO
import json

from flask import render_template, request, redirect, Response, url_for, flash
from flask_login import login_required
from prosaic.parsing import process_text
from prosaic.generation import poem_from_template

from ..app import app
from ..models import Source, Corpus, corpora_sources, Phrase, Template, Session
from ..util import get_method, auth_context, ResponseData, StringIOWrapper

def index() -> ResponseData:
    return render_template('index.html', **auth_context(request))

@login_required
def corpora() -> ResponseData:
    method = get_method(request)
    session = Session()

    if method == 'GET':
        context = auth_context(request)
        context.update({'corpora': session.query(Corpus).all(),
                        'sources': session.query(Source).all(),})
        return render_template('corpora.html', **context)

    if method == 'POST':
        c = Corpus()
        c.name = request.form['corpus_name']
        c.description = request.form['corpus_description']
        for source_id in request.form.getlist('sources'):
            s = session.query(Source).filter(Source.id==source_id).one()
            c.sources.append(s)
        session.add(c)
        session.commit()
        return redirect(url_for('corpus', corpus_id=c.id))

@login_required
def corpus(corpus_id: str) -> ResponseData:
    method = get_method(request)
    session = Session()

    if method == 'GET':
        context = auth_context(request)
        c = session.query(Corpus).filter(Corpus.id == corpus_id).one()
        source_ids = map(lambda s: s.id, c.sources)

        other_sources = session.query(Source)\
                               .filter(Source.id.notin_(source_ids))\
                               .all()
        context.update({
            'corpus': c,
            'other_sources': other_sources,
        })
        return render_template('corpus.html', **context)

    if method == 'PUT':
        c = session.query(Corpus).filter(Corpus.id == corpus_id).one()
        c.name = request.form['corpus_name']
        c.description = request.form['corpus_description']
        source_ids = map(int, request.form.getlist('sources'))
        c.sources = session.query(Source).filter(Source.id.in_(source_ids)).all()
        session.commit()

        return redirect(url_for('corpora'))

    if method == 'DELETE':
        c = session.query(Corpus).filter(Corpus.id == corpus_id).one()
        c.sources = []
        session.commit()
        session.query(Corpus).filter(Corpus.id == corpus_id).delete()
        session.commit()

        return redirect(url_for('corpora'))

@login_required
def sources() -> ResponseData:
    method = get_method(request)
    session = Session()

    if method == 'GET':
        context = auth_context(request)
        sources = session.query(Source).all()
        for source in sources:
            source.content_preview = source.content[0:250] + '...'
        context.update({'sources':sources})

        return render_template('sources.html', **context)

    if method == 'POST':
        s = Source()
        s.name = request.form['source_name']
        s.description = request.form['source_description']
        content = None
        if len(request.form['content_paste']) > 0:
            content = StringIO(request.form['content_paste'])
        elif request.files.get('content_file'):
            content = StringIOWrapper(request.files['content_file'].stream)

        if content is None:
            flash('Got empty content for source.')
            return redirect(url_for('sources'))

        # TODO handle error
        source_id = process_text(app.config['DB'], s, content)
        content.close()

        return redirect(url_for('source', source_id=source_id))

@login_required
def source(source_id: str) -> ResponseData:
    method = request.form.get('_method', request.method)
    session = Session()

    if method == 'GET':
        context = auth_context(request)
        s = session.query(Source).filter(Source.id == source_id).one()
        context.update({
            'source':s,
        })
        return render_template('source.html', **context)

    if method == 'PUT':
        s = session.query(Source).filter(Source.id == source_id).one()
        s.name = request.form['source_name']
        s.description = request.form['source_description']
        new_content = request.form['source_content']
        if new_content != s.content:
            session.query(Phrase).filter(Phrase.source_id == s.id).delete()
            session.expunge(s)
            process_text(app.config['DB'], s, StringIO(new_content))
        session.commit()

        return redirect(url_for('sources'))

    if method == 'DELETE':
        # TODO for love of god get on delete cascade working
        s = session.query(Source).filter(Source.id==source_id).one()
        corpus_ids = session.query(corpora_sources.c.corpus_id).filter(
            corpora_sources.c.source_id == source_id
        ).all()
        for c in session.query(Corpus).filter(Corpus.id.in_(corpus_ids)):
            c.sources.remove(s)
        session.query(Phrase).filter(Phrase.source_id == source_id).delete()
        session.query(Source).filter(Source.id == source_id).delete()
        session.commit()

        return redirect(url_for('sources'))

@login_required
def phrases() -> ResponseData:
    method = get_method(request)
    session = Session()

    if method == 'DELETE':
        s = session.query(Source)\
                   .filter(Source.id == request.form['source'])\
                   .one()
        phrase_ids = map(int, request.form.getlist('phrases'))
        session.query(Phrase).filter(Phrase.id.in_(phrase_ids))\
                             .delete(synchronize_session='fetch')

        s.content = ' '.join(map(lambda p: p.raw, s.phrases))

        session.commit()

        flash('selected phrases have been deleted')

        return redirect(url_for('source', source_id=s.id))

@login_required
def templates() -> ResponseData:
    method = get_method(request)
    session = Session()

    if method == 'GET':
        context = auth_context(request)
        ts = session.query(Template).all()
        context.update({
            'templates': ts,
        })
        return render_template('templates.html', **context)

    if method == 'POST':
        t = Template(name=request.form['template_name'],
                     lines=json.loads(request.form['template_json']))
        session.add(t)
        session.commit()
        return redirect(url_for('template', template_id=t.id))

@login_required
def template(template_id: str) -> ResponseData:
    method = get_method(request)
    session = Session()

    if method == 'GET':
        context = auth_context(request)
        t = session.query(Template).filter(Template.id == template_id).one()
        context.update({
            'template': t,
        })

        return render_template('template.html', **context)

    if method == 'PUT':
        t = session.query(Template).filter(Template.id == template_id).one()
        t.name = request.form['template_name']
        t.lines = json.loads(request.form['template_json'])
        session.add(t)
        session.commit()
        return redirect(url_for('template', template_id=template_id))

    if method == 'DELETE':
        session.query(Template).filter(Template.id == template_id).delete()
        session.commit()
        return redirect(url_for('templates'))

@login_required
def generate() -> ResponseData:
    method = get_method(request)
    session = Session()

    if method == 'GET':
        context = auth_context(request)
        cs = session.query(Corpus).all()
        ts = session.query(Template).all()
        context.update({
            'corpora': cs,
            'templates': ts,
        })

        return render_template('generate.html', **context)

    if method == 'POST':
        corpus_id = request.form['corpus_id']
        corpus_name = session.query(Corpus.name)\
                             .filter(Corpus.id==corpus_id)\
                             .one()[0]
        t = json.loads(request.form['template_tweak'])
        poem = poem_from_template(t, app.config['DB'], corpus_id)
        source_ids = set(map(lambda p: p[1], poem))
        get_source_name = lambda sid:\
                          session.query(Source.name).filter(Source.id==sid).one()[0]
        ss = map(
            lambda sid: {'id':sid, 'name': get_source_name(sid)},
            source_ids
        )

        result = {
            'corpus': {
                'id': corpus_id,
                'name': corpus_name,
            },
            'lines': list(map(lambda p: p[0], poem)),
            'used_sources': list(ss),
        }

        return json.dumps(result)
