import streamlit as st
import time
from openai import OpenAI
import time
from datetime import datetime, timezone
import boto3
import random
import string

#############################################################################
client = OpenAI(organization=st.secrets["organization"],
                api_key=st.secrets["api_key"],
                project="Prisma")

#############################################################################

def send_message(assist_id: str, question: str):

  def retrive_run_return_message(run_id: str, thread_id: str):
   if client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id).status == "completed":
      return client.beta.threads.messages.list(thread_id).data[0].content[0].text.value
   else:
      time.sleep(0.000001)
      return retrive_run_return_message(run_id, thread_id)
  
  
  run = client.beta.threads.create_and_run(
    assistant_id=st.secrets["assist_id"],
    thread={
    "messages": [
      {"role": "user", "content": question}
    ]
  }
)

  return {"answer": retrive_run_return_message(run.id, run.thread_id),
          "thread_id": run.thread_id}

def send_message_inside_context(assist_id: str, question: str):
    
    thread_id = retrive_last_register("prisma_database")["Item"]["thread_id"]

    def retrive_run_return_message(run_id: str, thread_id: str):
      if client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id).status == "completed":
        return client.beta.threads.messages.list(thread_id).data[0].content[0].text.value
      else:
        time.sleep(0.000001)
        return retrive_run_return_message(run_id, thread_id)

    message = client.beta.threads.messages.create(thread_id=thread_id,
                                        role="user",
                                        content=question)
    
    run = client.beta.threads.runs.create(
      assistant_id=st.secrets["assist_id"],
      thread_id=thread_id)

    return {"answer": retrive_run_return_message(run.id, run.thread_id),
          "thread_id": run.thread_id}



def retrive_last_register(table_name: str):
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                                  aws_access_key_id=st.secrets["aws_access_key_id"], aws_secret_access_key=st.secrets["aws_secret_access_key"])  
        name = table_name
        table = dynamodb.Table(name)
        response = table.scan()

        dict_transactions = {datetime.strptime(qa_entry['data'], "%m/%d/%Y %H:%M:%S") : [dados['id_transacao'] for dados in response["Items"] if any(qa['data'] == qa_entry['data'] for qa in dados['questions_answers_list'])][0]
                    for dados in response["Items"]
                    for qa_entry in dados['questions_answers_list']}  

        last_transaction = dict_transactions[max([date for date in dict_transactions.keys()])]

        last_transaction_complete = table.get_item(TableName=table_name,Key={"id_transacao": last_transaction})

        return last_transaction_complete

def return_time_since_last_transaction(last_transaction):
         last_transaction_time = max([datetime.strptime(item["data"], "%m/%d/%Y %H:%M:%S") for item in last_transaction])
         date_now = get_current_time_GMT().replace(tzinfo=None, microsecond=0)

         timedelta = date_now-last_transaction_time

         return timedelta 

def get_current_time_GMT():
    current_time_utc = datetime.now(timezone.utc)
    
    current_time_gmt = current_time_utc.astimezone(timezone.utc)
    
    return current_time_gmt

def create_register(table_name: str, item: dict):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                              aws_access_key_id=st.secrets["aws_access_key_id"], aws_secret_access_key=st.secrets["aws_secret_access_key"])  
    name = table_name
    table = dynamodb.Table(name)
    table.put_item(Item=item)

def generate_transaction_id(n: int):
  letters = string.ascii_letters + string.digits
  code = ''.join(random.choice(letters) for _ in range(n))
  return code

def update_is_useful_feedback(table_name: str, id_transacao: str, is_useful: bool):
         
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                                  aws_access_key_id=st.secrets["aws_access_key_id"], aws_secret_access_key=st.secrets["aws_secret_access_key"])  

        name = table_name

        table = dynamodb.Table(name)
         
        table.update_item(Key={"id_transacao": id_transacao},
                UpdateExpression="set #is_useful_feedback=:d",
                ExpressionAttributeNames={"#is_useful_feedback": "is_useful"},
                ExpressionAttributeValues={":d": is_useful},
                ReturnValues="UPDATED_NEW")

def update_feedback_txt(table_name: str, id_transacao: str, feedback_txt: str):
         
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                                  aws_access_key_id=st.secrets["aws_access_key_id"], aws_secret_access_key=st.secrets["aws_secret_access_key"])  

        name = table_name

        table = dynamodb.Table(name)
         
        table.update_item(Key={"id_transacao": id_transacao},
                UpdateExpression="set #feedback_comment=:d",
                ExpressionAttributeNames={"#feedback_comment": "feedback_txt"},
                ExpressionAttributeValues={":d": feedback_txt},
                ReturnValues="UPDATED_NEW")



last_register = retrive_last_register("prisma_database")["Item"]["questions_answers_list"]

time_since_last_register = return_time_since_last_transaction(last_register).seconds



# Função que inverte a string fornecida pelo usuário
def call_openai_assistant(user_input):
    
    return_object = send_message(st.secrets["assist_id"], user_input)
    
    return return_object

# Configuração do estado da sessão
if 'page' not in st.session_state:
    st.session_state['page'] = 'main'

if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ''

if 'result' not in st.session_state:
    st.session_state['result'] = ''

if 'is_useful' not in st.session_state:
    st.session_state['is_useful'] = None

if 'additional_feedback' not in st.session_state:
    st.session_state['additional_feedback'] = ''

# Função para exibir a página principal
def main_page():
    st.set_page_config(page_title="prIsmA: A inteligência Artificial do Monitor DF-e Protheus", page_icon=":pencil:")

    st.title("prIsmA: A inteligência Artificial do Monitor DF-e Protheus")

    user_input = st.text_area("Digite a sua pergunta:", height=200)

    if st.button("Submeter"):
        with st.spinner("Processando..."):
            
            openai_return = call_openai_assistant(user_input)

            st.session_state['user_input'] = user_input
            st.session_state['result'] = openai_return["answer"]
            st.session_state['page'] = 'feedback'
            
            ########################################################
            register = {"id_transacao": generate_transaction_id(10),
                "thread_id": openai_return["thread_id"],
                "questions_answers_list":[{
                    "qa_code": generate_transaction_id(5),
                    "data": f"{get_current_time_GMT().month}/{get_current_time_GMT().day}/{get_current_time_GMT().year} {get_current_time_GMT().hour}:{get_current_time_GMT().minute}:{get_current_time_GMT().second}",
                    "pergunta": user_input,
                    "resposta": openai_return["answer"]}]}
            create_register("prisma_database", register)
            ########################################################


            st.rerun()



# Função para exibir a página de feedback
def feedback_page():
    st.write("Você digitou:", st.session_state['user_input'])
    st.write("Resultado:", st.session_state['result'])
    st.write("### O resultado foi útil?")
    col1, col2 = st.columns(2)

    if col1.button("👍 Sim"):
        st.session_state['is_useful'] = 'Useful'
        st.session_state['page'] = 'thank_you'
        update_is_useful_feedback("prisma_database",
                                  retrive_last_register("prisma_database")["Item"]["id_transacao"],
                                  True)
        st.rerun()

    if col2.button("👎 Não"):
        st.session_state['is_useful'] = 'Not Useful'
        update_is_useful_feedback("prisma_database",
                                  retrive_last_register("prisma_database")["Item"]["id_transacao"],
                                  False)
        st.rerun()

    if st.session_state['is_useful'] == 'Not Useful':
        additional_feedback = st.text_area("Por favor, nos diga como podemos melhorar:")
        if st.button("Enviar Feedback"):
            st.session_state['additional_feedback'] = additional_feedback
            update_is_useful_feedback("prisma_database",
                                  retrive_last_register("prisma_database")["Item"]["id_transacao"],
                                  False)
            update_feedback_txt("prisma_database",
                                retrive_last_register("prisma_database")["Item"]["id_transacao"],
                                  additional_feedback)
            st.session_state['page'] = 'thank_you'
            st.rerun()

# Função para exibir a página de agradecimento
def thank_you_page():
    if st.session_state['is_useful'] == 'Useful':
        st.write("Obrigado pelo feedback! 👍")
    elif st.session_state['is_useful'] == 'Not Useful':
        st.write("Obrigado pelo feedback! 👎")
        st.write("Seu feedback adicional:", st.session_state['additional_feedback'])

    if st.button("Voltar"):
        st.session_state['page'] = 'main'
        st.session_state['is_useful'] = None
        st.rerun()

# Roteamento das páginas
if st.session_state['page'] == 'main':
    main_page()
elif st.session_state['page'] == 'feedback':
    feedback_page()
elif st.session_state['page'] == 'thank_you':
    thank_you_page()