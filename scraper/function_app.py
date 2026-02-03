import azure.functions as func

app = func.FunctionApp()

# Register Staatsoper scraper
import scraper_staatsoper
app.register_functions(scraper_staatsoper.bp)
