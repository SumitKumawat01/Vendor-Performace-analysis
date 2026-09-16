import logging
import sqlite3
import pandas as pd
from ingestion_db import ingest_db


# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------

logging.basicConfig(
    filename="logs/get_vendor_summary.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)


# ---------------------------------------------------------
# Create Vendor Summary
# ---------------------------------------------------------

def create_vendor_summary(conn):

    """
    This function merges different tables
    to create the overall vendor summary.
    """

    vendor_sales_summary = pd.read_sql_query("""

        WITH FreightSummary AS (

            SELECT
                VendorNumber,
                SUM(Freight) AS FreightCost

            FROM vendor_invoice

            GROUP BY VendorNumber

        ),

        PurchaseSummary AS (

            SELECT
                p.VendorNumber,
                p.VendorName,
                p.Brand,
                p.Description,
                p.PurchasePrice,

                pp.Price AS ActualPrice,
                pp.Volume,

                SUM(p.Quantity) AS TotalPurchaseQuantity,
                SUM(p.Dollars) AS TotalPurchaseDollars

            FROM purchases p

            JOIN purchase_prices pp
                ON p.Brand = pp.Brand

            WHERE p.PurchasePrice > 0

            GROUP BY
                p.VendorNumber,
                p.VendorName,
                p.Brand,
                p.Description,
                p.PurchasePrice,
                pp.Price,
                pp.Volume

        ),

        SalesSummary AS (

            SELECT
                VendorNo,
                Brand,

                SUM(SalesQuantity) AS TotalSalesQuantity,
                SUM(SalesDollars) AS TotalSalesDollars,
                SUM(SalesPrice) AS TotalSalesPrice,
                SUM(ExciseTax) AS TotalExciseTax

            FROM sales

            GROUP BY
                VendorNo,
                Brand

        )

        SELECT

            ps.VendorNumber,
            ps.VendorName,
            ps.Brand,
            ps.Description,

            ps.PurchasePrice,
            ps.ActualPrice,
            ps.Volume,

            ps.TotalPurchaseQuantity,
            ps.TotalPurchaseDollars,

            ss.TotalSalesQuantity,
            ss.TotalSalesDollars,
            ss.TotalSalesPrice,
            ss.TotalExciseTax,

            fs.FreightCost

        FROM PurchaseSummary ps

        LEFT JOIN SalesSummary ss
            ON ps.VendorNumber = ss.VendorNo
            AND ps.Brand = ss.Brand

        LEFT JOIN FreightSummary fs
            ON ps.VendorNumber = fs.VendorNumber

        ORDER BY
            ps.TotalPurchaseDollars DESC

    """, conn)

    return vendor_sales_summary


# ---------------------------------------------------------
# Clean Data
# ---------------------------------------------------------

def clean_data(df):

    """
    This function cleans the data
    and creates new columns for analysis.
    """

    # Convert Volume to numeric
    df['Volume'] = pd.to_numeric(
        df['Volume'],
        errors='coerce'
    )

    # Fill missing values
    df.fillna(0, inplace=True)

    # Remove extra spaces
    df['VendorName'] = (
        df['VendorName']
        .astype(str)
        .str.strip()
    )

    df['Description'] = (
        df['Description']
        .astype(str)
        .str.strip()
    )

    # -----------------------------------------------------
    # Gross Profit
    # -----------------------------------------------------

    df['GrossProfit'] = (
        df['TotalSalesDollars']
        - df['TotalPurchaseDollars']
    )

    # -----------------------------------------------------
    # Profit Margin
    # -----------------------------------------------------

    df['ProfitMargin'] = (
        df['GrossProfit']
        /
        df['TotalSalesDollars'].replace(0, pd.NA)
    ) * 100

    # -----------------------------------------------------
    # Stock Turnover
    # -----------------------------------------------------

    df['StockTurnover'] = (
        df['TotalSalesQuantity']
        /
        df['TotalPurchaseQuantity'].replace(0, pd.NA)
    )

    # -----------------------------------------------------
    # Sales to Purchase Ratio
    # -----------------------------------------------------

    df['SalesToPurchaseRatio'] = (
        df['TotalSalesDollars']
        /
        df['TotalPurchaseDollars'].replace(0, pd.NA)
    )

    # Replace generated missing values with 0
    df.fillna(0, inplace=True)

    return df


# ---------------------------------------------------------
# Main Program
# ---------------------------------------------------------

if __name__ == '__main__':

    try:

        # -------------------------------------------------
        # Creating Database Connection
        # -------------------------------------------------

        conn = sqlite3.connect('inventory.db')

        logging.info(
            'Database connection created successfully.'
        )

        # -------------------------------------------------
        # Creating Vendor Summary
        # -------------------------------------------------

        logging.info(
            'Creating Vendor Summary Table.....'
        )

        summary_df = create_vendor_summary(conn)

        logging.info(
            f'Vendor summary created. Shape: {summary_df.shape}'
        )

        print(
            "Vendor summary created:",
            summary_df.shape
        )

        # -------------------------------------------------
        # Cleaning Data
        # -------------------------------------------------

        logging.info(
            'Cleaning Data.....'
        )

        clean_df = clean_data(summary_df)

        logging.info(
            f'Data cleaned successfully. Shape: {clean_df.shape}'
        )

        # -------------------------------------------------
        # Save Data into SQLite Database
        # -------------------------------------------------

        logging.info(
            'Ingesting data into vendor_sales_summary table.....'
        )

        ingest_db(
            clean_df,
            'vendor_sales_summary',
            conn
        )

        logging.info(
            'Vendor summary successfully saved into database.'
        )

        # -------------------------------------------------
        # Export Data to CSV
        # -------------------------------------------------

        csv_file = 'vendor_sales_summary.csv'

        clean_df.to_csv(
            csv_file,
            index=False
        )

        logging.info(
            f'CSV file created successfully: {csv_file}'
        )

        print(
            f"CSV file created successfully: {csv_file}"
        )

        # -------------------------------------------------
        # Display First 5 Rows
        # -------------------------------------------------

        print("\nFirst 5 rows:")
        print(clean_df.head())

        # -------------------------------------------------
        # Close Database Connection
        # -------------------------------------------------

        conn.close()

        logging.info(
            'Database connection closed.'
        )

        logging.info(
            'Vendor summary process completed successfully.'
        )

        print(
            "\nVendor summary created successfully!"
        )

    except Exception as e:

        logging.error(
            f'Error occurred: {e}',
            exc_info=True
        )

        print(
            f"Error occurred: {e}"
        )