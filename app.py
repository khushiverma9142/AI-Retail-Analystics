import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from google import genai


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AI Retail Analytics",
    page_icon="🤖",
    layout="wide"
)


# =====================================================
# AIVEN MYSQL CONNECTION
# =====================================================

db_url = URL.create(
    drivername="mysql+pymysql",
    username=st.secrets["MYSQL_USER"],
    password=st.secrets["MYSQL_PASSWORD"],
    host=st.secrets["MYSQL_HOST"],
    port=int(st.secrets["MYSQL_PORT"]),
    database=st.secrets["MYSQL_DATABASE"]
)

engine = create_engine(
    db_url,
    connect_args={"ssl": {}}
)


# =====================================================
# GEMINI CONNECTION
# =====================================================

client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)


# =====================================================
# GEMINI: NATURAL LANGUAGE → SQL
# =====================================================

def generate_sql(question):

    prompt = f"""
You are an expert MySQL SQL generator.

We have a MySQL table named `customer`.

The columns are:

- customer_id
- age
- gender
- item_purchased
- category
- purchase_amount
- location
- size
- color
- season
- review_rating
- subscription_status
- shipping_type
- discount_applied
- previous_purchases
- payment_method
- frequency_of_purchases
- age_group
- purchase_frequency_days

Convert the user's question into a MySQL query.

Rules:

1. Use ONLY the `customer` table.
2. Use ONLY the columns listed above.
3. Return ONLY the SQL query.
4. Do NOT use markdown.
5. Do NOT explain the query.
6. Use meaningful aliases.
7. Generate READ-ONLY SQL only.
8. Do not use INSERT, UPDATE, DELETE, DROP, ALTER,
   CREATE, TRUNCATE or REPLACE.

User question:
{question}
"""

    response = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    sql = response.output_text.strip()

    # Remove markdown fences if Gemini adds them
    sql = sql.replace("```sql", "")
    sql = sql.replace("```", "")
    sql = sql.strip()

    return sql


# =====================================================
# SQL SAFETY CHECK
# =====================================================

def is_safe_sql(sql):

    sql_upper = sql.upper().strip()

    if not (
        sql_upper.startswith("SELECT")
        or sql_upper.startswith("WITH")
    ):
        return False

    forbidden_words = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "REPLACE"
    ]

    for word in forbidden_words:

        if word in sql_upper:
            return False

    # Prevent multiple SQL statements
    if sql.count(";") > 1:
        return False

    return True


# =====================================================
# STREAMLIT UI
# =====================================================

st.title("🤖 AI Retail Analytics")

st.write(
    "Ask questions about customer data using natural language "
    "and get answers powered by Gemini AI."
)


# =====================================================
# TOTAL CUSTOMERS
# =====================================================

try:

    result = pd.read_sql(
        "SELECT COUNT(*) AS total_customers FROM customer;",
        engine
    )

    st.metric(
        "Total Customers",
        int(result.iloc[0]["total_customers"])
    )

except Exception:

    st.error(
        "❌ Could not connect to the cloud database."
    )

    st.stop()


# =====================================================
# QUESTION INPUT
# =====================================================

question = st.text_input(
    "Ask a question about your customers:",
    placeholder="Example: Which category has the highest revenue?"
)


# =====================================================
# ANALYZE
# =====================================================

if st.button("🔍 Analyze"):

    if not question:

        st.warning("Please enter a question.")

    else:

        try:

            # Gemini generates SQL
            with st.spinner("🤖 Gemini is generating SQL..."):

                sql = generate_sql(question)


            st.write("### Your Question")

            st.write(question)


            # Security check
            if not is_safe_sql(sql):

                st.error(
                    "❌ Unsafe SQL generated. "
                    "Only read-only queries are allowed."
                )

                st.stop()


            # Show generated SQL
            st.write("### Generated SQL")

            st.code(
                sql,
                language="sql"
            )


            # Execute SQL on Aiven
            with st.spinner("📊 Analyzing customer data..."):

                result = pd.read_sql(
                    sql,
                    engine
                )


            # Display result
            st.write("### Result")

            st.dataframe(
                result,
                use_container_width=True
            )


        except Exception as e:

            st.error(
                f"Something went wrong:\n\n{str(e)}"
            )