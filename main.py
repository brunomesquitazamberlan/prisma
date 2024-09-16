import streamlit as st
import time
from openai import OpenAI
import time
from datetime import datetime, timezone
import random
import string
import firebase_admin
from firebase_admin import credentials, firestore


#######################################################################
# Verifique se já existe um app inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate('rag_base_conhecimento.json')
    firebase_admin.initialize_app(cred)

# Conectar ao Firestore
db = firestore.client()
########################################################################

#############################################################################
client = OpenAI(organization=st.secrets["organization"],
                api_key=st.secrets["api_key"])

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


def get_current_time_GMT():
    current_time_utc = datetime.now(timezone.utc)
    
    current_time_gmt = current_time_utc.astimezone(timezone.utc)
    
    return current_time_gmt

def create_register(collection_name: str, item: dict):
    
    # Referência à coleção existente
    collection_ref = db.collection(collection_name)

    # Adicionar um documento com um ID gerado automaticamente
    doc_ref = collection_ref.add(item)

    return doc_ref[1].id
    
def update_register(collection_name: str, item_id: str, info_to_update: dict):

    try:
        doc_ref = db.collection(colecao).document(doc_id)

        doc_ref.update(dados_atualizados)

        return True
    
    except:
        return False
        

def generate_transaction_id(n: int):
  letters = string.ascii_letters + string.digits
  code = ''.join(random.choice(letters) for _ in range(n))
  return code

def update_is_useful_feedback(collection_name: str, id_transacao: str, is_useful: bool):
         
        info_to_update = {"is_useful": is_useful}

        #collection_name: str, item_id: str, info_to_update: dict 
        return update_register(collection_name, id_transacao, info_to_update)
        

def update_feedback_txt(collection_name: str, id_transacao: str, feedback: str):
         
        info_to_update = {"feedback": feedback}

        #collection_name: str, item_id: str, info_to_update: dict 
        return update_register(collection_name, id_transacao, info_to_update)

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
            
            document_id = create_register("prisma", register)
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
        
        #update_is_useful_feedback(collection_name: str, id_transacao: str, is_useful: bool)
        
        ubpdate_is_useful_feedback("prisma", document_id, True)
        st.rerun()

    if col2.button("👎 Não"):
        st.session_state['is_useful'] = 'Not Useful'
        ubpdate_is_useful_feedback("prisma", document_id, False)
        st.rerun()

    if st.session_state['is_useful'] == 'Not Useful':
        additional_feedback = st.text_area("Por favor, nos diga como podemos melhorar:")
        if st.button("Enviar Feedback"):
            st.session_state['additional_feedback'] = additional_feedback
            #update_is_useful_feedback("prisma_database",
            #                      retrive_last_register("prisma_database")["Item"]["id_transacao"],
            #                      False)
            update_feedback_txt("prisma",
                                document_id,
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