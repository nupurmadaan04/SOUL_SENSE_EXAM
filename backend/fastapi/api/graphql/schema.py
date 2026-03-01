from fastapi import APIRouter
from graphene import ObjectType, String, Int, Field, List
from graphene_fasterapi import generate_fastapi_schema

router = APIRouter()


class User(ObjectType):
    id = Int()
    username = String()
    email = String()
    created_at = String()


class Exam(ObjectType):
    id = Int()
    title = String()
    description = String()
    duration = Int()
    created_by = String()


class Question(ObjectType):
    id = Int()
    text = String()
    question_type = String()
    options = List(String)


class Journal(ObjectType):
    id = Int()
    title = String()
    content = String()
    mood = String()
    created_at = String()


class Query(ObjectType):
    users = List(User)
    user = Field(User, id=Int(required=True))
    exams = List(Exam)
    exam = Field(Exam, id=Int(required=True))
    questions = List(Question)
    journals = List(Journal)
    journal = Field(Journal, id=Int(required=True))

    def resolve_users(self, info):
        return []

    def resolve_user(self, info, id):
        return {"id": id, "username": "sample", "email": "sample@example.com"}

    def resolve_exams(self, info):
        return []

    def resolve_exam(self, info, id):
        return {"id": id, "title": "Sample Exam", "description": "Sample"}

    def resolve_questions(self, info):
        return []

    def resolve_journals(self, info):
        return []

    def resolve_journal(self, info, id):
        return {"id": id, "title": "Sample", "content": "Content", "mood": "happy"}


schema = generate_fastapi_schema(Query)

router.add_api_route("/graphql", schema, methods=["GET", "POST"])
