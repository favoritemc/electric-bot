import os
import re
from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract

app = Flask(__name__)

# 配置上传文件的文件夹
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保 Tesseract 的路径正确
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    # 从表单中获取数据
    base_price_old = float(request.form['base_price_old'])
    transmission_price = float(request.form['transmission_price'])
    line_loss_price = float(request.form['line_loss_price'])
    system_operation_price = float(request.form['system_operation_price'])
    flat_usage = float(request.form['flat_usage'])
    valley_usage = float(request.form['valley_usage'])
    peak_usage = float(request.form['peak_usage'])
    sharp_peak_usage = float(request.form['sharp_peak_usage'])
    transformer_capacity = float(request.form['transformer_capacity'])
    capacity_price_per_unit = float(request.form['capacity_price_per_unit'])
    power_factor_adjustment_fee = float(request.form['power_factor_adjustment_fee'])
    new_reference_price = float(request.form['new_reference_price'])

    # 调用计算逻辑
    old_total_fee, new_total_fee, saving_amount = perform_calculation(
        base_price_old, transmission_price, line_loss_price, system_operation_price,
        flat_usage, valley_usage, peak_usage, sharp_peak_usage,
        transformer_capacity, capacity_price_per_unit, power_factor_adjustment_fee, new_reference_price
    )

    return render_template('result.html', old_total_fee=old_total_fee, new_total_fee=new_total_fee,
                           saving_amount=saving_amount)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(file_path)
        file.save(file_path)

        # 使用 OCR 解析图片
        text = pytesseract.image_to_string(Image.open(file_path), lang='chi_sim')
        print(text)
        # 解析提取文本中的数据
        extracted_data = extract_data_from_text(text)

        # 调用计算函数
        old_total_fee, new_total_fee, saving_amount = perform_calculation(
            extracted_data['base_price_old'], extracted_data['transmission_price'],
            extracted_data['line_loss_price'], extracted_data['system_operation_price'],
            extracted_data['flat_usage'], extracted_data['valley_usage'],
            extracted_data['peak_usage'], extracted_data['sharp_peak_usage'],
            extracted_data['transformer_capacity'], extracted_data['capacity_price_per_unit'],
            extracted_data['power_factor_adjustment_fee'], extracted_data['new_reference_price']
        )

        return render_template('result.html', old_total_fee=old_total_fee, new_total_fee=new_total_fee,
                               saving_amount=saving_amount)

    return redirect(request.url)


def extract_data_from_text(text):
    data = {}

    data['flat_usage'] = float(re.search(r'平\s*(\d+\.\d+)', text).group(1))
    data['valley_usage'] = float(re.search(r'谷\s*(\d+\.\d+)', text).group(1))
    data['peak_usage'] = float(re.search(r'峰\s*(\d+\.\d+)', text).group(1))
    data['sharp_peak_usage'] = float(re.search(r'尖\s*(\d+\.\d+)', text).group(1))

    data['base_price_old'] = float(re.search(r'代理购电基准电价[^\d]*(\d+\.\d+)', text).group(1))
    data['transmission_price'] = float(re.search(r'输配电价[^\d]*(\d+\.\d+)', text).group(1))
    data['line_loss_price'] = float(re.search(r'上网环节线损电价[^\d]*(\d+\.\d+)', text).group(1))
    data['system_operation_price'] = float(re.search(r'系统运行费单价[^\d]*(\d+\.\d+)', text).group(1))

    # 基本电费提取
    transformer_match = re.search(r'电压等级容量\s*(\d+)KVA\s*\*\s*单价\s*(\d+\.\d+)', text)
    data['transformer_capacity'] = float(transformer_match.group(1))
    data['capacity_price_per_unit'] = float(transformer_match.group(2))

    data['power_factor_adjustment_fee'] = float(re.search(r'功率因数调整电费[^\d]*(\d+\.\d+)', text).group(1))

    data['new_reference_price'] = 0.55  # 假设的新参考电价

    return data


def perform_calculation(base_price_old, transmission_price, line_loss_price, system_operation_price,
                        flat_usage, valley_usage, peak_usage, sharp_peak_usage,
                        transformer_capacity, capacity_price_per_unit, power_factor_adjustment_fee,
                        new_reference_price):
    old_flat_price = base_price_old + transmission_price + line_loss_price + system_operation_price

    valley_price = 0.38 * old_flat_price
    peak_price = 1.7 * old_flat_price
    sharp_peak_price = 2.125 * old_flat_price
    old_energy_fee = (flat_usage * old_flat_price) + (valley_usage * valley_price) + \
                     (peak_usage * peak_price) + (sharp_peak_usage * sharp_peak_price)
    basic_fee = transformer_capacity * capacity_price_per_unit

    old_total_fee = old_energy_fee + basic_fee + power_factor_adjustment_fee

    new_flat_price = new_reference_price + transmission_price + line_loss_price + system_operation_price
    new_valley_price = 0.38 * new_flat_price
    new_peak_price = 1.7 * new_flat_price
    new_sharp_peak_price = 2.125 * new_flat_price
    new_energy_fee = (flat_usage * new_flat_price) + (valley_usage * new_valley_price) + \
                     (peak_usage * new_peak_price) + (sharp_peak_usage * new_sharp_peak_price)

    new_total_fee = new_energy_fee + basic_fee + power_factor_adjustment_fee

    saving_amount = old_total_fee - new_total_fee

    return old_total_fee, new_total_fee, saving_amount


if __name__ == '__main__':
    app.run(debug=True)

