# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import sys
import mysql.connector
from datetime import datetime

def getProductDetails(cursor, orderID):
    command = (
        "SELECT ProductID, Quantity FROM order_details WHERE OrderID = %s"
    )
    cursor.execute(command, (orderID,))
    return cursor.fetchall()

def addInventoryTransaction(cursor, productDetails, orderID):
    base = ""
    now = datetime.now().strftime('\'%Y-%m-%d %H:%M:%S\'')
    template = """INSERT INTO inventory_transactions 
    (TransactionType, TransactionCreatedDate, ProductID, Quantity, CustomerOrderID)
VALUES (1, {}, {}, {}, {});"""
    for id, quantity in productDetails:
        base += template.format(now, id, quantity, orderID)
    command = ("""
        START TRANSACTION;
        BEGIN;
        UPDATE orders SET ShipperID = 1, ShippingFee = 5.00, ShippedDate={date}
        WHERE OrderID={id};
        {commands}
        COMMIT;
    """.format(commands=base, id=orderID, date=now))
    print(command)
    cursor.execute(command, multi=True)
    print("Order shipped")

def quantityAvailable(cursor, productID):
    command = (
        """
        SELECT qty FROM
        (SELECT sum(Quantity) - total AS qty, inventory_transactions.ProductID
        FROM inventory_transactions
        JOIN
            (SELECT sum(Quantity) as total, ProductID
            FROM inventory_transactions
            WHERE TransactionType > 1 GROUP BY ProductID)
            AS neg On neg.ProductID = inventory_transactions.ProductID
        WHERE TransactionType = 1 GROUP BY ProductID
        ORDER BY ProductID) AS items
        WHERE ProductID = %s
    """
    )
    cursor.execute(command, (productID,))
    return cursor.fetchone()[0]


def shipOrder(cursor, orderID):
    productDetails = getProductDetails(cursor, orderID)
    if not productDetails:
        print("Order does not exist")
        return
    for id, quantityNeeded in productDetails:
        if quantityNeeded > quantityAvailable(cursor, id):
            print("Order can't be shipped")
            return
    addInventoryTransaction(cursor, productDetails, orderID)


def printPendingOrders(cursor):
    command = (
        """SELECT OrderID, ShipName, OrderDate
            FROM orders
            WHERE ShippedDate IS NULL
            ORDER BY OrderDate
        """
    )
    cursor.execute(command)
    results = cursor.fetchall()
    print("Order ID,    Customer,    Date")
    for line in results:
        ID, Customer, Date = line
        print("{:^6}, {:^10}, {:^12}".format(ID, Customer, Date.strftime("%m/%d/%Y")))


def splitOnCapital(string):
    if string.isupper():
        return string
    strings = []
    last_index = 0
    for index, char in enumerate(string):
        if char in [x for x in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"][1:]:
            strings.append(string[last_index:index])
            last_index = index
    if strings:
        return (" ".join(strings) + " " + string[last_index:]).strip()
    else:
        return string


def deleteOrder(id, cursor):
    preview = "SELECT OrderID, ShipName, OrderDate FROM orders WHERE OrderID = %s"
    cursor.execute(preview, (id,))
    preview_data = cursor.fetchone()
    if not preview_data:
        print("Order not found")
        print("Cancelling...")
        return
    print("Order ID,    Customer,    Date")
    ID, Customer, Date = preview_data
    print("{:^6}, {:^10}, {:^12}".format(ID, Customer, Date.strftime("%m/%d/%Y")))
    print("Are you sure you would like to delete Y/N?")
    i = input()
    if i.strip().lower() != 'y':
        print("Canceled")
        return
    command = (
        """START TRANSACTION;
        BEGIN;
        DELETE FROM order_details where OrderID = %s;
        DELETE FROM invoices WHERE OrderID= %s;
        DELETE FROM orders where OrderID = %s;
        COMMIT;
        """
    )
    cursor.execute(command, (id, id, id), multi=True)

def createOrder(cursor):
    print("Please input the customer id for this order:")
    customer_id = input()
    print("Please input all of the product ids for this order.")
    print("When done press enter")
    ans = [input()]
    while ans[-1]:
        ans.append(input())
    base = ""
    template = """
        INSERT INTO order_details(OrderID, ProductID, Quantity, UnitPrice, Discount, StatusID)
        SELECT @last_id, ID, {0}, ListPrice, 0, 0 FROM products
        WHERE id={0} AND Discontinued=0;
    """
    for p_id in ans[:-1]:
        base = base + "\n " + template.format(p_id)


    commad = (
        """ START TRANSACTION;
        BEGIN;
        INSERT INTO orders(EmployeeID, CustomerID, OrderDate, ShipName, ShipAddress,
                           ShipCity, ShipState, ShipZIP, ShipCountry)
        SELECT 1, 12, NOW(), CONCAT(FirstName, " ", LastName), Address, City, State, ZIP, Country FROM customers
        WHERE id=12;
        SET @last_id = LAST_INSERT_ID();
        """ + "\n " + base + "\n Commit;"
    )
    print(commad)
    cursor.execute(commad, multi=True)
    print("Order Sumbitted")

def addCustomerToDB(fields, values, cursor):
    values_list = []
    fields.remove("ID")
    fields.remove("Attachments")
    for field in fields:
        values_list.append("'{}'".format(values[splitOnCapital(field)]))
    command = (
        """
           START TRANSACTION;
           BEGIN;
           INSERT INTO Customers ({})
           VALUES ({});
           COMMIT;
        """.format(", ".join(fields), ", ".join(values_list))
    )
    print(command)
    cursor.execute(command, multi=True)
    query = (
        "SELECT * FROM Customers;"
    )
    cursor.execute(query)
    for item in cursor.fetchall():
        print(item)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':


    # Connect with the MySQL Server
    cnx = mysql.connector.connect(user='admin', password='admin', database='northwind')

    curA = cnx.cursor(buffered=True)

    query = (
        "SHOW COLUMNS FROM Customers"
    )
    curA.execute(query)
    results = curA.fetchall()
    db_customer_fields = [x[0] for x in results]
    customer_fields = [splitOnCapital(x[0]) for x in results]
    customer_fields.remove("ID")
    customer_fields.remove("Attachments")
    while True:
        print(
            """1. Add a customer
2. Add an order
3. Remove an order
4. Ship an order
5. Print pending orders
6. More Options
7. Exit""")
        choice = input()
        if choice == "1":
            print("For each field enter the information and press enter")
            print("To skip a field press enter without typing anything else")
            print("To redo the last field type 'r' and hit enter")
            print("You may only redo one field. To restart type cancel and press enter")
            ans = {}
            for field in customer_fields:
                last_field = field
                #done = False
                print(field)
                response = input().strip()
                if response == "cancel":
                    ans = None
                    break
                elif response == "r":
                    print(last_field)
                    ans[last_field] = input().strip()
                    print(field)
                    ans[field] = input().strip()
                else:
                    ans[field] = response
            if ans:
                addCustomerToDB(db_customer_fields, ans, curA)
        if choice == "2":
            createOrder(curA)
        if choice == "3":
            print("Please enter the ID of the order you'd like to delete")
            id = int(input())
            deleteOrder(id, curA)
        if choice == "4":
            print("Please enter the ID of the order you'd like to ship")
            id = int(input())
            shipOrder(curA, id)
        if choice == "5":
            printPendingOrders(curA)
        if choice == "7":
            sys.exit()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
