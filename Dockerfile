FROM python:3.9.17-slim-bullseye
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt 
EXPOSE 8000
CMD [ "python", "app.py" ]
