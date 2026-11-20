CREATE TABLE orders (
    ordernum INT,
    itemnum INT,          
    quantity INT, 
    storeid VARCHAR(20),   
    vendorid VARCHAR(20)       
);
CREATE TABLE store (
    storeid VARCHAR(20),
    name VARCHAR(25)
);
CREATE TABLE item (
    itemnum INT,
    price DECIMAL(12,2)
);
CREATE TABLE vendorOutstanding(
    vendorid VARCHAR(20),
    amount DECIMAL(12,2)
);
CREATE TABLE storeOutstanding (
    storeid VARCHAR(20),
    amount DECIMAL(12,2)
);
