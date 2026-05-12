import os
import sys
import json

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from infrastructure.db.models import CleanJobDB
from infrastructure.db.session import SessionLocal
from sqlalchemy import select

def run_normalization():
    with SessionLocal() as session:
        try:
            search_terms = ["Natural Language Processing", "Artificial Intelligence", "Computer Vision", "Machine Learning", "Large Language Models"]
            correct_terms = ["NLP", "AI", "CV", "ML","LLM"]

            # We loop through our pairs
            for i, search_val in enumerate(search_terms):
                correct_val = correct_terms[i]
                
                # 1. Query for jobs containing this specific term
                query = select(CleanJobDB).where(CleanJobDB.domain_knowledge.contains(search_val))
                jobs_to_update = session.execute(query).scalars().all()

                print(f"Checking for '{search_val}': Found {len(jobs_to_update)} matches.")

                for job in jobs_to_update:
                    current_tags = job.domain_knowledge
                    
                    # 2. Check for the INDIVIDUAL term (search_val), not the whole list
                    if search_val in current_tags:
                        new_tags = []
                        for tag in current_tags:
                            if search_val in tag:
                                new_tags.append(correct_val)
                            else:
                                new_tags.append(tag)
                        
                        # 3. Update the job object
                        job.domain_knowledge = new_tags
            
            # 4. Commit once at the very end for efficiency
            session.commit()
            print("Successfully normalized all terms!")

        except Exception as e:
            session.rollback()
            print(f"Error: {e}")

if __name__ == "__main__":
    run_normalization()
