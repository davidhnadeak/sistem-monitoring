# Sistem Monitoring/server/app.py

# Import library
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from boto3.dynamodb.conditions import Key
from tensorflow import keras
from datetime import datetime
import os
import boto3
import joblib
import pandas as pd
import logging

# Load environment variable
load_dotenv()

# Mengambil credential dari environment variable
region = os.getenv('AWS_REGION')
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
dynamodb_table = os.getenv('DYNAMODB_TABLE')

# Menginisialisasi DynamoDB client
dynamodb = boto3.resource(
    'dynamodb',
    region_name=region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

# Load model
model = keras.models.load_model('model/multilayer-perceptron.h5')
scaler = joblib.load('model/scaler.pkl')

# Create Flask app
app = Flask(__name__)

# Function untuk mengubah timestamp menjadi datetime
def formatted_timestamp(timestamp):
    try:
        # Mengubah nilai datetime dari milidetik ke detik
        dt = datetime.fromtimestamp(int(timestamp) / 1000)

        # Menyimpan nama-nama hari dan bulan
        days_list = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]
        months_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                       "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

        # Mengambil nama hari, tanggal, bulan, tahun, dan waktu
        day_name = days_list[dt.weekday()]
        day = f"{dt.day:02d}"
        month_name = months_list[dt.month - 1]
        year = dt.year
        time = dt.strftime("%H:%M:%S")

        return {
            "datetime": f"{day_name}, {day} {month_name} {year} - {time}",
            "date": f"{day_name}, {day} {month_name} {year}",
            "time": time
        }
    except Exception as e:
        return {
            "datetime": "Invalid Timestamp",
            "date": "-",
            "time": "-"
        }

# Route untuk mengambil dan mengolah 1 baris data terbaru
@app.route('/kualitas-air-tanah', methods=['GET'])
def get_groundwater_quality():
    try:
        # Mengambil parameter 'kode_pos'
        kode_pos = request.args.get('kode_pos')

        if not kode_pos:
            logging.warning(f"Warning in air_tanah_processing: Missing required parameter (kode_pos)")
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameter (kode_pos)'
            }), 400

        # Menentukan table yang akan diakses
        table = dynamodb.Table(dynamodb_table)

        """
        Melakukan query terhadap table untuk mengambil data terbaru berdasarkan partition key (kode_pos), 
        mengurutkan data secara descending berdasarkan sort key (timestamp),
        dan hanya mengambil maksimal 300 item
        """
        response = table.query(
            IndexName='kode_pos-timestamp-index',
            KeyConditionExpression=Key('kode_pos').eq(int(kode_pos)),
            ScanIndexForward=False, 
            Limit=300
        )

        # Menyimpan hasil query ke dalam sebuah list
        items = response['Items']

        if not items:
            logging.warning(f'Warning in get_groundwater_quality: No records found for postal code: {kode_pos}')
            return jsonify({
                'status': 'error',
                'message': f'No records found for postal code: {kode_pos}'
            }), 400

        # Memasukkan items ke dalam DataFrame
        df = pd.DataFrame(items)

        # Menentukan feature
        features = ['ph', 'temperature', 'tds', 'turbidity']

        # Menghapus baris yang memiliki nilai NaN
        df = df.dropna(subset=features)

        # Mengubah tipe data feature ke float
        df[features] = df[features].astype('float64')

        if df.empty:
            logging.warning(f'Warning in get_groundwater_quality: No valid records found for postal code: {kode_pos}')
            return jsonify({
                'status': 'error',
                'message': f'No valid records found for postal code: {kode_pos}'
            }), 400

        # Mempersiapkan data untuk diprediksi
        input_data = df[features]

        # Feature scaling
        input_data = scaler.transform(input_data)

        # Melakukan prediksi
        prediction_probs = model.predict(input_data)
        prediction_classes = (prediction_probs > 0.5).astype(int)

        # Mapping hasil prediksi ke target klasifikasi kualitas air tanah
        target_mapping = {
            0: "Layak Minum",
            1: "Tidak Layak Minum"
        }

        for i, item in enumerate(items):
            # Menambahkan hasil prediksi ke setiap item
            pred_target = target_mapping.get(int(prediction_classes[i]), "Tidak Diketahui")
            item['model_classification'] = pred_target

            # Menambahkan datetime, date, dan time ke setiap item
            if 'timestamp' in item:
                formatted = formatted_timestamp(item['timestamp'])
                item['datetime'] = formatted['datetime']
                item['date'] = formatted['date']
                item['time'] = formatted['time']

        # Mengembalikan response
        logging.info(f"Success in air_tanah_processing: Records retrieved and processed successfully")
        return jsonify({
            'status': 'success',
            'message': 'Records retrieved and processed successfully',
            'data': items
        }), 200
    
    except Exception as e:
        logging.error(f"Error in air_tanah_processing: {e}")
        return jsonify({
            'status': 'error',
            'message': 'An internal server error occurred while retrieving water quality records'
        }), 500

# Route untuk mengambil data kode_pos
@app.route('/kode-pos', methods=['GET'])
def get_kode_pos():
    try:
        # Menentukan table yang akan diakses
        table = dynamodb.Table(dynamodb_table)

        # Melakukan scan terhadap seluruh item di dalam table
        response = table.scan()

        # Menyimpan hasil scan ke dalam sebuah list
        items = response['Items']

        if not items:
            logging.warning(f"Warning in get_kode_pos: Table is empty")
            return jsonify({
                'status': 'error',
                'message': 'No records found'
            }), 404

        # Mempersiapkan dictionary untuk menyimpan kode_pos yang unik beserta kelurahannya
        unique_kode_pos = {}

        for item in items:
            kode_pos = item['kode_pos']
            kelurahan = item['kelurahan']
            
            # Menyimpan kode_pos dan kelurahan hanya jika kode_pos belum pernah disimpan ke dalam dictionary
            if kode_pos not in unique_kode_pos:
                unique_kode_pos[kode_pos] = {
                    'kode_pos': kode_pos,
                    'kelurahan': kelurahan
                }

        # Mengonversi dictionary menjadi list
        result = list(unique_kode_pos.values())

        if not result:
            logging.warning(f"Warning in get_kode_pos: No unique postal code records found")
            return jsonify({
                'status': 'error',
                'message': 'No unique postal code records found'
            }), 404

        # Mengembalikan response
        logging.info(f"Success in get_kode_pos: Unique postal code records retrieved successfully")
        return jsonify({
            'status': 'success',
            'message': 'Unique postal code records retrieved successfully',
            'data': result
        }), 200
    
    except Exception as e:
        logging.error(f"Error in get_kode_pos: {e}")
        return jsonify({
            'status': 'error',
            'message': 'An internal server error occurred while retrieving unique postal code records'
        }), 500

# Run server
if __name__ == '__main__':
    app.run(debug=True)
