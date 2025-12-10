from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Annotated
from database import engine, sessionLocal
import models
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session
import uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


app = FastAPI()
models.Base.metadata.create_all(bind=engine)

class ChoiceBase(BaseModel):
    choice_text: str
    is_correct: bool

class QuestionBase(BaseModel):
    question_text: str
    choices: List[ChoiceBase]


def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

@app.get("/questions/{question_id}", status_code=status.HTTP_200_OK)
async def read_question(question_id: int, db: db_dependency):
    result = db.query(models.Questions).filter(models.Questions.id == question_id).first()
    if not result:
        raise HTTPException(status_code=404, detail='Question is not found')
    return result

@app.get("/choices/{question_id}", status_code=status.HTTP_200_OK)
async def read_choices(question_id: int, db: db_dependency):
    result = db.query(models.Choices).filter(models.Choices.question_id == question_id).all()
    if not result:
        raise HTTPException(status_code=404, detail='Choices is not found')
    return result

@app.post("/questions/", status_code =status.HTTP_201_CREATED)
async def create_questions(question: QuestionBase, db: db_dependency):
    db_question = models.Questions(question_text=question.question_text)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    for choice in question.choices:
        db_choice = models.Choices(choice_text=choice.choice_text, is_correct = choice.is_correct, question_id=db_question.id)
        db.add(db_choice)
    db.commit()
    return {"message": "The Question is created along with the Choices"}

@app.delete("/choices/{question_id}", status_code=204)
async def delete_choice(question_id: int, db: db_dependency):
    db_choice = db.query(models.Choices).filter(models.Choices.question_id == question_id).first()
    if not db_choice:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_choice)
    db.commit()

    return {"message": "choice deleted successfully"}

@app.get("/questions/", status_code=status.HTTP_200_OK)
async def read_all_questions(db: Session = Depends(get_db)):
    db_tickets = db.query(models.Questions).all()
    
    # 2. Check if any results were found
    if not db_tickets:

        return [] 
    
    return db_tickets

@app.get("/choices/", status_code=status.HTTP_200_OK)
async def read_all_choices(db: Session = Depends(get_db)):
    db_tickets = db.query(models.Choices).all()
    
    # 2. Check if any results were found
    if not db_tickets:
        return [] 
    
    return db_tickets


@app.delete("/questions/{id}", status_code=204)
async def delete_question(id: int, db: Session = Depends(get_db)):

    question = (
        db.query(models.Questions)
        .filter(models.Questions.id == id)
        .first()
    )

    if question is None:
        raise HTTPException(404, "Question not found")

    # delete related choices first
    choices = (
        db.query(models.Choices)
        .filter(models.Choices.question_id == id)
        .all()
    )

    for choice in choices:
        db.delete(choice)

    db.delete(question)
    db.commit()

    return {"message": "Question deleted successfully"}


@app.get("/all_data_retrival/",status_code=status.HTTP_200_OK)
async def get_all_data(db: Session = Depends(get_db)):
    users = (
        db.query(models.Questions)
        .options(joinedload(models.Questions.choices))
        .all()
    )

    if not users:
        raise HTTPException(404, "Data Not found")
    return users

@app.get("/all-data_individual", status_code=status.HTTP_200_OK)
async def get_separate_data(db: Session = Depends(get_db)):
    questions = db.query(models.Questions).all()
    choices = db.query(models.Choices).all()
    return {
        "no_questions": len(questions),
        "no_choices": len(choices),
        "Questions": questions,
        "Choices": choices
    }


# This is to get the flat data (but the questions are repeating in this code)
@app.get("/flat-data", status_code=status.HTTP_200_OK)
def get_flat_data1(db: Session = Depends(get_db)):
    results = (
        db.query(models.Questions, models.Choices)
        .join(models.Questions, models.Questions.id == models.Choices.question_id)
        .all()
    )

    response = []

    for questions, choices in results:
        response.append({
            "question_id": questions.id,
            "question_text": questions.question_text,
            "choice_id": choices.id,
            "choice":choices.choice_text,
            "is_correct": choices.is_correct
        })

    return response


#This is the flat corrected API which gives data properly with the questions
@app.get("/flat-data", status_code=status.HTTP_200_OK)
def get_flat_data2(db: Session = Depends(get_db)):
    results = (
        db.query(models.Questions, models.Choices)
        .join(models.Choices, models.Questions.id == models.Choices.question_id)
        .all()
    )

    grouped = {}

    for question, choice in results:

        if question.id not in grouped:
            grouped[question.id] = {
                "question_id": question.id,
                "question_text": question.question_text
            }

        # Count choices
        index = sum(1 for k in grouped[question.id] if k.startswith("choice_") and k.endswith("_id")) + 1

        grouped[question.id][f"choice_{index}_id"] = choice.id
        grouped[question.id][f"choice_{index}_text"] = choice.choice_text
        grouped[question.id][f"choice_{index}_is_correct"] = choice.is_correct

    return list(grouped.values()) #JSON array that gets return to the client
 