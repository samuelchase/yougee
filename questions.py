from google.appengine.api import search
import webapp2
import logging
import json

from models import AnswersDS
from models import QuestionDS


_INDEX_NAME = 'question'
INDEX_SKILL = search.Index(name=_INDEX_NAME)


def return_message(status, description, data):
    message = dict(status=status, description=description, data=data)
    return json.dumps(message)


def createQuestionDoc(cq_key, **kwargs):
    doc = search.Document(
        fields=[search.TextField(name='rep_id', value=kwargs['rep_id']),
                search.TextField(
                    name='partner_id', value=kwargs['partner_id']),
                search.TextField(
                    name='reason', value=kwargs['reason']),
                search.TextField(
                    name='question', value=kwargs['question']),
                search.TextField(
                    name='question_key', value=str(cq_key)),

                ]

    )
    add_items = INDEX_SKILL.put(doc)
    doc_id = add_items[0].id
    return str(doc_id)


def doc_search(search_string, user_id):
    query_options = search.QueryOptions(
        limit=1000,
        returned_fields=['question_key']
    )

    query = search.Query(query_string=search_string, options=query_options)
    results_querry = INDEX_SKILL.search(query)
    results = results_querry.results
    logging.info(str(results))
    if results:
        question_keys = []
        for result in results:
            question_key = result.fields[0].value
            question_keys.append(question_key)

        list_dicts = []
        for key in question_keys:
            entity = QuestionDS.urlsafe_get(key)
            logging.info(entity)
            permission = json.loads(entity.assign)
            if user_id == 'master_admin':
                logging.info(user_id)
                list_dicts.append(entity.to_dict())
            else:
                if permission[user_id]:
                    list_dicts.append(entity.to_dict())
                    logging.info('list list_dicts')
                    logging.info(list_dicts)
        return list_dicts
    else:
        return 'no search results'


def updateQuestionDoc(**kwargs):
    logging.info('get doc id')
    logging.info(kwargs['document_id'])
    doc = search.Document(
        doc_id=kwargs['document_id'],
        fields=[search.TextField(name='rep_id', value=kwargs['rep_id']),
                search.TextField(
                    name='partner_id', value=kwargs['partner_id']),
                search.TextField(
                    name='reason', value=kwargs['reason']),
                search.TextField(
                    name='question', value=kwargs['question']),
                search.TextField(
                    name='question_key', value=kwargs['question_key'])
                ]
    )
    INDEX_SKILL.put(doc)
    return 'updated doc'


def deleteQuestionDoc(doc_id):
    obj = INDEX_SKILL.delete(doc_id)
    return obj


def to_dict(doc_obj):
    field_value_list = doc_obj.fields
    doc_obj_dict = {}
    for f in field_value_list:
        doc_obj_dict[f.name] = f.value
    return doc_obj_dict


class searchForQuestion(webapp2.RequestHandler):

    def get(self):
        q_string = self.request.get('search_string')
        search_string = q_string.replace(' ', ' OR ')
        logging.info(search_string)
        user_id = self.request.get('user_id')
        data = doc_search(str(search_string), user_id)
        message = return_message('success', 'question found', data)
        self.response.write(message)


class updateQuestion(webapp2.RequestHandler):

    def post(self):
        obj = json.loads(self.request.body)
        qsDS = QuestionDS.urlsafe_get(obj['question_key'])
        qsDS.rep_ID = obj['rep_id']
        qsDS.partner_ID = obj['partner_id']
        qsDS.reason = obj['reason']
        qsDS.question = obj['question']
        qsDS.created_by = obj['created_by']
        qsDS.document_id = obj['document_id']
        qsDS.next_node = obj['next_node']
        qsDS.prev_node = obj['prev_node']
        qsDS.question_key = obj['question_key']
        qsDS.campaign_key = obj['campaign_key']
        qsDS.question_image = obj['question_image']
        qsDS.question_video = obj['question_video']
        qsDS.assign = str(json.dumps(obj['assign']))
        qsDS.order = int(obj['order'])
        qsDS.put()
        data = dict(key=obj['question_key'])
        message = return_message('success', 'updated questions', data)
        self.response.write(message)


def look_up_permission(all_q, feed):
    q_list = []
    for a in all_q:
        if feed == 'all':
            q_list.append(a.to_dict())
        else:
            permission = json.loads(a.assign)
            logging.info(permission)
            if feed not in permission:
                permission['client'] = False
                logging.info(permission)
                qsDS = QuestionDS.urlsafe_get(a.key())
                qsDS.assign = str(json.dumps(permission))
                qsDS.put()
            else:
                if permission[feed]:
                    q_list.append(a.to_dict())
    return q_list


class getAllQuestions(webapp2.RequestHandler):

    def get(self):
        feed = self.request.get('feed')
        if feed == 'all':
            limit = 10
        else:
            limit = 10
        offset = int(self.request.get('offset'))
        q = QuestionDS.query()
        q.order(QuestionDS.order)
        all_q = q.fetch(limit, offset=offset)
        q_return = look_up_permission(all_q, feed)
        message = return_message('success', 'get all questions', q_return)
        self.response.write(message)


class createQuestion(webapp2.RequestHandler):
    def post(self):
        obj = json.loads(self.request.body)
        logging.info('create question')
        logging.info(obj)
        cq = QuestionDS(
            rep_ID=obj['rep_id'],
            partner_ID=obj['partner_id'],
            reason=obj['reason'],
            question=obj['question'],
            created_by=obj['created_by'],
            campaign_key=obj['campaign_key'],
            question_image=obj['question_image'],
            question_video=obj['question_video'],
            intro=obj['intro'],
            order=int(obj['order']),
            assign=str(json.dumps(obj['assign'])))
        cq.put()
        cq_key = cq.key.urlsafe()
        doc_id = createQuestionDoc(cq_key, **obj)
        cq.document_id = doc_id
        cq.put()

        logging.info('doc id')
        logging.info(doc_id)

        data = dict(key=str(cq_key))
        message = return_message('success', 'created new question', data)
        self.response.write(message)


class totalAnswers(webapp2.RequestHandler):
    def get(self):
        q_key = self.request.get('q_key')
        answers = AnswersDS.query(AnswersDS.question_key == q_key)
        logging.info(answers.count())
        self.response.write(answers.count())


class deleteQuestion(webapp2.RequestHandler):
    def get(self):
        question_key = self.request.get('question_key')
        document_id = self.request.get('document_id')
        deleteQuestionDoc(document_id)
        question = QuestionDS.urlsafe_get(question_key)
        question.delete()
        self.response.write('deleted')
