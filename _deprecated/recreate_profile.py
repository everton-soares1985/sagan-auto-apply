import json
profile = {
  "first_name": "SEU_NOME",
  "last_name": "SEU_SOBRENOME",
  "email": "seu_email@exemplo.com",
  "phone": "+5511999999999",
  "job_title": "Seu Cargo Atual",
  "current_salary": "5000",
  "academic_level": "Bachelors",
  "age": "26-30",
  "salary_expectation": "3000",
  "gender": "Male",
  "industry": "Technology",
  "cv_file_path": "./curriculo.pdf",
  "cover_letter": "Dear Hiring Team, I am very interested in this position and believe my skills align well with the requirements."
}
with open("candidate_profile.json", "w", encoding="utf-8") as f:
    json.dump(profile, f, ensure_ascii=False, indent=2)
print("recriado")
