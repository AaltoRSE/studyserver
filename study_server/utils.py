import csv
from django.http import HttpResponse

def data_to_csv_response(data, filename):
    if not data:
        return HttpResponse("No data available", content_type='text/plain')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.DictWriter(response, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    return response