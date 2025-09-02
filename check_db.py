#!/usr/bin/env python3
"""Check database content for debugging."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config.settings import settings

def check_database():
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check document count
        doc_count = session.execute(text('SELECT COUNT(*) FROM documents')).scalar()
        print(f'Documents in database: {doc_count}')

        # Check extracted info count
        extracted_count = session.execute(text('SELECT COUNT(*) FROM extracted_information')).scalar()
        print(f'Extracted information records: {extracted_count}')

        # Check if we have any feedback_motivation data
        feedback_count = session.execute(text("SELECT COUNT(*) FROM extracted_information WHERE feedback_motivation IS NOT NULL AND feedback_motivation != '[]'")).scalar()
        print(f'Records with feedback data: {feedback_count}')

        # Sample some data
        if doc_count > 0:
            print('\nSample documents:')
            docs = session.execute(text('SELECT employee_name, file_path FROM documents LIMIT 3')).fetchall()
            for doc in docs:
                print(f'  - {doc.employee_name}: {doc.file_path}')

        if feedback_count > 0:
            print('\nSample feedback data:')
            feedback = session.execute(text("SELECT feedback_motivation FROM extracted_information WHERE feedback_motivation IS NOT NULL AND feedback_motivation != '[]' LIMIT 2")).fetchall()
            for f in feedback:
                print(f'  - {f.feedback_motivation[:200]}...')
        
        # Check risks_concerns data
        risks_count = session.execute(text("SELECT COUNT(*) FROM extracted_information WHERE risks_concerns IS NOT NULL AND risks_concerns != '[]'")).scalar()
        print(f'\nRecords with risks/concerns data: {risks_count}')

    finally:
        session.close()

if __name__ == "__main__":
    check_database()