package customerinfo.app;

import android.os.Bundle;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.*;

public class MainActivity extends AppCompatActivity {

    private EditText meterInput;
    private Button prepaidBtn, postpaidBtn, submitBtn, exitBtn;
    private TextView resultView;
    private String selectedType = "prepaid";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        initViews();
        setupClickListeners();
    }

    private void initViews() {
        meterInput = findViewById(R.id.meterInput);
        prepaidBtn = findViewById(R.id.prepaidBtn);
        postpaidBtn = findViewById(R.id.postpaidBtn);
        submitBtn = findViewById(R.id.submitBtn);
        exitBtn = findViewById(R.id.exitBtn);
        resultView = findViewById(R.id.resultView);
        updateButtonStates();
    }

    private void setupClickListeners() {
        prepaidBtn.setOnClickListener(v -> {
            selectedType = "prepaid";
            updateButtonStates();
            showResult("📱 Prepaid selected - Enter 12-digit meter number");
        });

        postpaidBtn.setOnClickListener(v -> {
            selectedType = "postpaid";
            updateButtonStates();
            showResult("💡 Postpaid selected - Enter meter number");
        });

        submitBtn.setOnClickListener(v -> {
            String meterNo = meterInput.getText().toString().trim();
            if (meterNo.isEmpty()) {
                showResult("❌ Please enter meter number");
                return;
            }

            if (selectedType.equals("prepaid") && meterNo.length() != 12) {
                showResult("❌ Prepaid meter must be 12 digits");
                return;
            }

            fetchData(meterNo);
        });

        exitBtn.setOnClickListener(v -> finish());
    }

    private void updateButtonStates() {
        prepaidBtn.setBackgroundColor(selectedType.equals("prepaid") ? 0xFF3498DB : 0xFF95A5A6);
        postpaidBtn.setBackgroundColor(selectedType.equals("postpaid") ? 0xFF3498DB : 0xFF95A5A6);
    }

    private void fetchData(String meterNo) {
        showResult("🔄 Fetching " + selectedType + " data...\nMeter: " + meterNo);

        new Thread(() -> {
            try {
                Map<String, Object> result;
                if (selectedType.equals("prepaid")) {
                    result = fetchPrepaidData(meterNo);
                } else {
                    result = fetchPostpaidData(meterNo);
                }

                String output = displayResult(result, selectedType);
                runOnUiThread(() -> showResult(output));

            } catch (Exception e) {
                runOnUiThread(() -> showResult("❌ Error: " + e.getMessage() + "\n\nCheck internet connection and try again."));
            }
        }).start();
    }

    private void showResult(String message) {
        runOnUiThread(() -> resultView.setText(message));
    }

    // API Methods
    private Map<String, Object> api1Lookup(String meterNumber) {
        try {
            String cleanMeter = meterNumber.trim();
            URL url = new URL("http://web.bpdbprepaid.gov.bd/bn/token-check");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Accept", "text/x-component");
            conn.setRequestProperty("Content-Type", "text/plain;charset=UTF-8");
            conn.setRequestProperty("Next-Action", "29e85b2c55c9142822fe8da82a577612d9e58bb2");
            conn.setRequestProperty("Origin", "http://web.bpdbprepaid.gov.bd");
            conn.setRequestProperty("Referer", "http://web.bpdbprepaid.gov.bd/bn/token-check");
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
            
            String requestData = "[{\"meterNo\":\"" + cleanMeter + "\"}]";
            conn.setDoOutput(true);
            
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = requestData.getBytes("utf-8");
                os.write(input, 0, input.length);
            }
            
            if (conn.getResponseCode() == 200) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                String line;
                String jsonLine = null;
                
                while ((line = reader.readLine()) != null) {
                    if (line.startsWith("1:")) {
                        jsonLine = line.substring(2);
                        break;
                    }
                }
                
                if (jsonLine != null) {
                    JSONObject api1Data = new JSONObject(jsonLine);
                    String consumerNumber = extractConsumerNumber(api1Data);
                    
                    Map<String, Object> result = new HashMap<>();
                    result.put("consumer_number", consumerNumber);
                    result.put("api1_data", api1Data.toString());
                    return result;
                } else {
                    Map<String, Object> error = new HashMap<>();
                    error.put("error", "No valid response data found");
                    return error;
                }
            } else {
                Map<String, Object> error = new HashMap<>();
                error.put("error", "HTTP Error: " + conn.getResponseCode());
                return error;
            }
        } catch (Exception e) {
            Map<String, Object> error = new HashMap<>();
            error.put("error", "API 1 Error: " + e.getMessage());
            return error;
        }
    }

    private String extractConsumerNumber(JSONObject api1Data) {
        try {
            if (api1Data.has("mCustomerData")) {
                JSONObject customerData = api1Data.getJSONObject("mCustomerData");
                if (customerData.has("result")) {
                    JSONObject result = customerData.getJSONObject("result");
                    if (result.has("customerAccountNo")) {
                        String customerNo = getText(result.get("customerAccountNo"));
                        if (customerNo != null && !customerNo.equals("N/A")) {
                            return customerNo;
                        }
                    }
                }
            }
            
            if (api1Data.has("mOrderData")) {
                JSONObject orderData = api1Data.getJSONObject("mOrderData");
                if (orderData.has("result")) {
                    JSONObject result = orderData.getJSONObject("result");
                    if (result.has("orders")) {
                        JSONObject orders = result.getJSONObject("orders");
                        if (orders.has("order")) {
                            Object orderObj = orders.get("order");
                            if (orderObj instanceof JSONArray) {
                                JSONArray orderArray = (JSONArray) orderObj;
                                if (orderArray.length() > 0) {
                                    JSONObject firstOrder = orderArray.getJSONObject(0);
                                    if (firstOrder.has("customerNo")) {
                                        String customerNo = getText(firstOrder.get("customerNo"));
                                        if (customerNo != null && !customerNo.equals("N/A")) {
                                            return customerNo;
                                        }
                                    }
                                }
                            } else if (orderObj instanceof JSONObject) {
                                JSONObject order = (JSONObject) orderObj;
                                if (order.has("customerNo")) {
                                    String customerNo = getText(order.get("customerNo"));
                                    if (customerNo != null && !customerNo.equals("N/A")) {
                                        return customerNo;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private Map<String, Object> api3Lookup(String customerNumber) {
        try {
            URL url = new URL("https://miscbillapi.bpdb.gov.bd/api/v1/get-pre-customer_info/" + customerNumber);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            
            conn.setRequestMethod("GET");
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
            conn.setRequestProperty("Accept", "application/json");
            
            if (conn.getResponseCode() == 200) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                
                JSONObject api3Data = new JSONObject(response.toString());
                if (api3Data.has("customerNumber")) {
                    Map<String, Object> result = new HashMap<>();
                    result.put("api3_data", api3Data.toString());
                    return result;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private Map<String, Object> api2Lookup(String accountNumber) {
        try {
            URL url = new URL("https://billonwebapi.bpdb.gov.bd/api/CustomerInformation/" + accountNumber);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            
            conn.setRequestMethod("GET");
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
            conn.setRequestProperty("Accept", "application/json");
            
            if (conn.getResponseCode() == 200) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                
                Map<String, Object> result = new HashMap<>();
                result.put("api2_data", response.toString());
                return result;
            } else {
                Map<String, Object> error = new HashMap<>();
                error.put("error", "HTTP Error: " + conn.getResponseCode());
                return error;
            }
        } catch (Exception e) {
            Map<String, Object> error = new HashMap<>();
            error.put("error", "API 2 Error: " + e.getMessage());
            return error;
        }
    }

    private Map<String, Object> fetchPrepaidData(String meterNumber) {
        Map<String, Object> api1Result = api1Lookup(meterNumber);
        Map<String, Object> result = new HashMap<>();
        
        result.put("meter_number", meterNumber);
        result.put("api1_data", api1Result.get("api1_data"));
        result.put("consumer_number", api1Result.get("consumer_number"));
        result.put("api3_data", null);
        result.put("api2_data", null);
        
        String consumerNumber = (String) api1Result.get("consumer_number");
        if (consumerNumber != null && !api1Result.containsKey("error")) {
            Map<String, Object> api3Result = api3Lookup(consumerNumber);
            if (api3Result != null) {
                result.put("api3_data", api3Result.get("api3_data"));
                
                try {
                    JSONObject api3Data = new JSONObject((String) api3Result.get("api3_data"));
                    String accountNumber = api3Data.optString("customerNumber");
                    
                    Map<String, Object> api2Result;
                    if (!accountNumber.isEmpty()) {
                        api2Result = api2Lookup(accountNumber);
                    } else {
                        api2Result = api2Lookup(consumerNumber);
                    }
                    result.put("api2_data", api2Result.get("api2_data"));
                } catch (Exception e) {
                    Map<String, Object> api2Result = api2Lookup(consumerNumber);
                    result.put("api2_data", api2Result.get("api2_data"));
                }
            } else {
                Map<String, Object> api2Result = api2Lookup(consumerNumber);
                result.put("api2_data", api2Result.get("api2_data"));
            }
        }
        
        return result;
    }

    private Map<String, Object> fetchPostpaidData(String meterNumber) {
        Map<String, Object> result = new HashMap<>();
        result.put("meter_number", meterNumber);
        result.put("api3_data", null);
        result.put("api2_data", null);
        
        Map<String, Object> api3Result = api3Lookup(meterNumber);
        if (api3Result != null) {
            result.put("api3_data", api3Result.get("api3_data"));
            
            try {
                JSONObject api3Data = new JSONObject((String) api3Result.get("api3_data"));
                String accountNumber = api3Data.optString("customerNumber");
                
                Map<String, Object> api2Result;
                if (!accountNumber.isEmpty()) {
                    api2Result = api2Lookup(accountNumber);
                } else {
                    api2Result = api2Lookup(meterNumber);
                }
                result.put("api2_data", api2Result.get("api2_data"));
            } catch (Exception e) {
                Map<String, Object> api2Result = api2Lookup(meterNumber);
                result.put("api2_data", api2Result.get("api2_data"));
            }
        } else {
            Map<String, Object> api2Result = api2Lookup(meterNumber);
            result.put("api2_data", api2Result.get("api2_data"));
        }
        
        return result;
    }

    private String getText(Object field) {
        try {
            if (field instanceof JSONObject) {
                JSONObject obj = (JSONObject) field;
                if (obj.has("_text")) {
                    return obj.getString("_text").trim();
                }
            }
            return field != null ? field.toString().trim() : "N/A";
        } catch (Exception e) {
            return "N/A";
        }
    }

    private String displayResult(Map<String, Object> result, String billType) {
        StringBuilder output = new StringBuilder();
        output.append("\n").append("=".repeat(50)).append("\n");
        output.append("📊 ").append(billType.toUpperCase()).append(" LOOKUP RESULTS\n");
        output.append("=".repeat(50)).append("\n");
        
        if (result.containsKey("error")) {
            output.append("❌ Error: ").append(result.get("error")).append("\n");
            return output.toString();
        }
        
        output.append("🔢 Meter Number: ").append(result.getOrDefault("meter_number", "N/A")).append("\n");
        
        if (billType.equals("prepaid") && result.get("consumer_number") != null) {
            output.append("👤 Consumer Number: ").append(result.get("consumer_number")).append("\n");
        }
        
        // Simplified display - you can add more formatting logic here
        output.append("\n✅ Data fetched successfully!\n");
        output.append("Check logs for detailed information.\n");
        
        return output.toString();
    }
}
