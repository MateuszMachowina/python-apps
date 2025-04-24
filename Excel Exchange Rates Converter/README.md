
# Currency Converter for Excel

This Python script helps convert invoice amounts in an Excel file from EUR to a target currency using real-time exchange rates fetched from [ExchangeRate-API](https://www.exchangerate-api.com/). It supports both `.xlsx` (standard Excel files) and `.xlsm` (macro-enabled Excel files), ensuring that the macros in `.xlsm` files are preserved.

## Features

- **Supports both `.xlsx` and `.xlsm` files**: Whether you are working with a standard or macro-enabled Excel file, this script handles both formats seamlessly.
- **Real-time exchange rates**: Fetches the exchange rate from [ExchangeRate-API](https://www.exchangerate-api.com/) for EUR to the target currency.
- **Invoice conversion**: Converts the net and gross invoice values into a target currency and adds the results into new columns.
- **File preservation**: The original file format is preserved and saved as a new file with the target currency appended to the filename (e.g., `sales_data_PLN.xlsx`).
- **Local Currency Output**: The converted values are placed in the designated columns in the Excel file.

## Requirements

Before running this script, make sure you have the following:

### Prerequisites

- **Python 3.13**
- **Libraries**:
  - `requests`
  - `openpyxl`
  - `python-dotenv`
  - `tkinter` (for file selection dialog)

### API Key

To fetch exchange rates, you will need an API key from [ExchangeRate-API](https://www.exchangerate-api.com/). Once you have the key, store it in a `.env` file in your project directory:

```env
ER_API_KEY=your-api-key-here
```

## How to Use

1. **Download the necessary files**  
   - The script, Excel files (found in the `sales-department-example` folder), and the `requirements.txt` file.
2. **Install required libraries**  

   ```bash
   pip install -r requirements.txt
   ```
3. **Create a `.env` file** in your project directory with your `ER_API_KEY`.
4. **Run the script**:

```bash
excel-exchange-rates-converter.py
```

5. **Select the Excel file** when prompted by the file dialog that appears.
6. **Enter the target currency** (e.g., `PLN`, `SEK`, `GBP`,  etc.).
7. The script will:
   - Fetch the exchange rate for EUR to the specified target currency.
   - Convert the values in the invoice net and gross columns into the target currency.
   - Save the updated file with the target currency appended to the filename (e.g., `sales_data_PLN.xlsx`).

### Example

- **Input file**: `sales_data.xlsx`
- **Target currency**: `PLN`
- **Output file**: `sales_data_PLN.xlsx`

The conversion will be applied, and the updated file will be saved in the same directory with the target currency appended to the filename.

## File Format & Conversion Details

- **Invoice Net**: Column `H`
- **Invoice Gross**: Column `I`
- **Converted Invoice Net**: Column `K` (Net converted to target currency)
- **Converted Invoice Gross**: Column `L` (Gross converted to target currency)
- **Target Currency**: Column `M` (Displays the target currency name, e.g., `PLN`)

### Important Notes

- The script automatically detects and processes a sheet whose name starts with **"sales"** (case-insensitive).
- The `ExchangeRate-API` key must be valid for the script to fetch the exchange rate successfully.
- If the input file is in `.xlsm` format, the macro functionality is preserved.

## Troubleshooting

- **No exchange rate found**: If there's an issue with fetching the exchange rate, the script will notify you. Ensure the API key is valid and the ExchangeRate-API service is up.
- **Invalid file format**: The script supports `.xlsx` and `.xlsm` files. If your file is in a different format, please convert it to `.xlsx` or `.xlsm`.
