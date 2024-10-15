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
    fund_additional_fee = float(request.form['fund_additional_fee'])

    # 调用计算逻辑
    results = perform_calculation(
        base_price_old, transmission_price, line_loss_price, system_operation_price,
        flat_usage, valley_usage, peak_usage, sharp_peak_usage,
        transformer_capacity, capacity_price_per_unit, power_factor_adjustment_fee,
        new_reference_price, fund_additional_fee
    )

    return render_template('result.html', **results)

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
        file.save(file_path)

        # 使用 OCR 解析图片
        text = pytesseract.image_to_string(Image.open(file_path), lang='chi_sim')

        # 解析提取文本中的数据
        extracted_data = extract_data_from_text(text)

        # 调用计算函数
        results = perform_calculation(
            extracted_data['base_price_old'], extracted_data['transmission_price'],
            extracted_data['line_loss_price'], extracted_data['system_operation_price'],
            extracted_data['flat_usage'], extracted_data['valley_usage'],
            extracted_data['peak_usage'], extracted_data['sharp_peak_usage'],
            extracted_data['transformer_capacity'], extracted_data['capacity_price_per_unit'],
            extracted_data['power_factor_adjustment_fee'], extracted_data['new_reference_price'],
            extracted_data['fund_additional_fee']
        )

        return render_template('result.html', **results)

    return redirect(request.url)


def extract_data_from_text(text):
    data = {}
    print(text)
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

    # 添加基金及附加费单价的提取
    data['fund_additional_fee'] = float(re.search(r'基金及附加费单价[^\d]*(\d+\.\d+)', text).group(1))

    return data


def perform_calculation(base_price_old, transmission_price, line_loss_price, system_operation_price,
                        flat_usage, valley_usage, peak_usage, sharp_peak_usage,
                        transformer_capacity, capacity_price_per_unit, power_factor_adjustment_fee,
                        new_reference_price, fund_additional_fee):
    print(f"Input parameters:")
    print(f"base_price_old: {base_price_old}")
    print(f"transmission_price: {transmission_price}")
    print(f"line_loss_price: {line_loss_price}")
    print(f"system_operation_price: {system_operation_price}")
    print(f"flat_usage: {flat_usage}")
    print(f"valley_usage: {valley_usage}")
    print(f"peak_usage: {peak_usage}")
    print(f"sharp_peak_usage: {sharp_peak_usage}")
    print(f"transformer_capacity: {transformer_capacity}")
    print(f"capacity_price_per_unit: {capacity_price_per_unit}")
    print(f"power_factor_adjustment_fee: {power_factor_adjustment_fee}")
    print(f"new_reference_price: {new_reference_price}")
    print(f"fund_additional_fee: {fund_additional_fee}")


    old_flat_price = base_price_old + transmission_price + line_loss_price + system_operation_price
    print(f"old_flat_price: {old_flat_price}")

    valley_price = round(0.38 * old_flat_price, 4)
    peak_price = round(1.7 * old_flat_price, 4)
    sharp_peak_price = round(2.125 * old_flat_price, 4)
    print(f"valley_price: {valley_price}")
    print(f"peak_price: {peak_price}")
    print(f"sharp_peak_price: {sharp_peak_price}")

    old_energy_fee = round(flat_usage * old_flat_price, 2) + round(valley_usage * valley_price, 2) + \
                     round(peak_usage * peak_price, 2) + round(sharp_peak_usage * sharp_peak_price, 2)
    # print(round(flat_usage * old_flat_price, 2))
    # print(round(valley_usage * valley_price, 2))
    # print(round(peak_usage * peak_price, 2))
    # print(round(sharp_peak_usage * sharp_peak_price, 2))

    print(f"old_energy_fee: {old_energy_fee}")

    basic_fee = transformer_capacity * capacity_price_per_unit
    print(f"basic_fee: {basic_fee}")

    total_usage = flat_usage + valley_usage + peak_usage + sharp_peak_usage
    print(f"total_usage: {total_usage}")

    fund_additional_charge = round(total_usage * fund_additional_fee, 2)
    print(f"fund_additional_charge: {fund_additional_charge}")

    old_total_fee = old_energy_fee + basic_fee + power_factor_adjustment_fee + fund_additional_charge
    print(f"old_total_fee: {old_total_fee}")

    new_flat_price = new_reference_price + transmission_price + line_loss_price + system_operation_price
    print(f"new_flat_price: {new_flat_price}")

    new_valley_price = round(0.38 * new_flat_price, 4)
    new_peak_price = round(1.7 * new_flat_price, 4)
    new_sharp_peak_price = round(2.125 * new_flat_price, 4)
    print(f"new_valley_price: {new_valley_price}")
    print(f"new_peak_price: {new_peak_price}")
    print(f"new_sharp_peak_price: {new_sharp_peak_price}")

    new_energy_fee = round(flat_usage * new_flat_price, 2) + round(valley_usage * new_valley_price, 2) + \
                     round(peak_usage * new_peak_price, 2) + round(sharp_peak_usage * new_sharp_peak_price, 2)
    print(f"new_energy_fee: {new_energy_fee}")

    new_total_fee = new_energy_fee + basic_fee + power_factor_adjustment_fee + fund_additional_charge
    print(f"new_total_fee: {new_total_fee}")

    saving_amount = old_total_fee - new_total_fee
    print(f"saving_amount: {saving_amount}")

    old_average_price = old_total_fee / total_usage if total_usage > 0 else 0
    new_average_price = new_total_fee / total_usage if total_usage > 0 else 0
    price_difference = old_average_price - new_average_price
    saving_percentage = (saving_amount / old_total_fee * 100) if old_total_fee > 0 else 0
    print(f"old_average_price: {old_average_price}")
    print(f"new_average_price: {new_average_price}")
    print(f"price_difference: {price_difference}")
    print(f"saving_percentage: {saving_percentage}")

    return {
        'old_total_fee': old_total_fee,
        'new_total_fee': new_total_fee,
        'old_average_price': old_average_price,
        'new_average_price': new_average_price,
        'price_difference': price_difference,
        'total_savings': saving_amount,
        'total_usage': total_usage,
        'saving_percentage': saving_percentage
    }

if __name__ == '__main__':
    app.run(debug=True)