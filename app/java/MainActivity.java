package customerinfo.app;

import android.os.Bundle;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends AppCompatActivity {

    private EditText meterInput;
    private Button prepaidBtn, postpaidBtn, submitBtn, exitBtn;
    private TextView resultView;
    private String selectedType = "prepaid";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Initialize Python once
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }

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
            showResult("ðŸ”‹ Prepaid selected - Enter 12-digit meter number");
        });

        postpaidBtn.setOnClickListener(v -> {
            selectedType = "postpaid";
            updateButtonStates();
            showResult("ðŸ’¡ Postpaid selected - Enter meter number");
        });

        submitBtn.setOnClickListener(v -> {
            String meterNo = meterInput.getText().toString().trim();
            if (meterNo.isEmpty()) {
                showResult("â�Œ Please enter meter number");
                return;
            }

            if (selectedType.equals("prepaid") && meterNo.length() != 12) {
                showResult("â�Œ Prepaid meter must be 12 digits");
                return;
            }

            fetchData(meterNo);
        });

        exitBtn.setOnClickListener(v -> {
            finish();
        });
    }

    private void updateButtonStates() {
        prepaidBtn.setBackgroundColor(selectedType.equals("prepaid") ? 0xFF3498DB : 0xFF95A5A6);
        postpaidBtn.setBackgroundColor(selectedType.equals("postpaid") ? 0xFF3498DB : 0xFF95A5A6);
    }

    private void fetchData(String meterNo) {
        showResult("ðŸ”„ Fetching " + selectedType + " data...\nMeter: " + meterNo);

        new Thread(() -> {
            try {
                Python py = Python.getInstance();
                PyObject api = py.getModule("api");

                PyObject result;
                if (selectedType.equals("prepaid")) {
                    result = api.callAttr("fetch_prepaid_data", meterNo);
                } else {
                    result = api.callAttr("fetch_postpaid_data", meterNo);
                }

                // Format the result using display_result function
                PyObject display_func = api.callAttr("display_result", result, selectedType);
                String output = display_func.toString();

                runOnUiThread(() -> showResult(output));

            } catch (Exception e) {
                runOnUiThread(() -> showResult("â�Œ Error: " + e.getMessage() + "\n\nCheck internet connection and try again."));
            }
        }).start();
    }

    private void showResult(String message) {
        runOnUiThread(() -> resultView.setText(message));
    }
}
