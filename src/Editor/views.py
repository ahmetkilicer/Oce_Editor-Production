from django.shortcuts import render, redirect, get_object_or_404
from .models import Folder, Asset, Presentation, AssetCoordinate, Product, Message, Notification
from error_logs.models import ErrorLog
from django.db.models import Count
from django.http import JsonResponse, HttpResponse, HttpRequest
import json
from django.views.decorators.csrf import csrf_exempt
import requests
from datetime import datetime
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from moviepy.editor import VideoFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from tempfile import NamedTemporaryFile
import cv2
from django.template.loader import render_to_string
import os
import zipfile
import shutil
import tempfile
from reportlab.pdfgen import canvas
import base64
import requests
from pathlib import Path
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

BASE_DIR = Path(__file__).resolve().parent.parent




@api_view(['GET', 'POST'])
@authentication_classes([BasicAuthentication])
def get_pre_names(request):
    if request.method == 'POST':
        productMessageList = request.data
        print(productMessageList)
        existing_products = Product.objects.all()
        existing_salesforce_ids = set()
        existing_messages = Message.objects.all()
        existing_salesforce_message_ids = set()
        updated_products = []
        updated_messages = []

        new_products = []
        new_messages = []

        product_data = []
        message_data = []

        for data in productMessageList:
            if 'ProductId' in data:
                # This dictionary represents product information
                product_data.append(data)
            elif 'MessageId' in data:
                # This dictionary represents message information
                message_data.append(data)
        
        for product in existing_products:
            existing_salesforce_ids.add(product.salesforce_id)

        for message in existing_messages:
            existing_salesforce_message_ids.add(message.salesforce_id)

        for product_info in product_data:
            salesforce_id = product_info['ProductId']
            name = product_info['ProductName']
            oce_is_active = product_info['ProductisActive']  # Assuming 'OCE_is_active' is present in the API data

            if salesforce_id in existing_salesforce_ids:
                existing_product = existing_products.get(salesforce_id=salesforce_id)
                if existing_product.name != name or existing_product.is_active != oce_is_active:
                    existing_product.name = name
                    existing_product.is_active = oce_is_active
                    updated_products.append(existing_product)
            else:
                new_product = Product(salesforce_id=salesforce_id, name=name, is_active=oce_is_active)
                new_products.append(new_product)

        # Process messages
        for message_info in message_data:
            message_id = message_info['MessageId']
            message_name = message_info['MessageName']
            message_product_id = message_info['MessageProductId']
        

            if message_id in existing_salesforce_message_ids:
                existing_message = existing_messages.get(salesforce_id=message_id)
                if existing_message:
                    if existing_message.name != message_name or existing_message.product != message_product_id:
                        existing_message.name = message_name
                    
                        existing_message.product = Product.objects.get(salesforce_id=message_product_id) 
                        updated_messages.append(existing_message)
            else:
                new_message = Message(salesforce_id=message_id, name=message_name, product = Product.objects.get(salesforce_id=message_product_id))
                new_messages.append(new_message)

        # Delete missing products
        missing_salesforce_ids = existing_salesforce_ids - set(product_info['ProductId'] for product_info in product_data)
        missing_products = Product.objects.filter(salesforce_id__in=missing_salesforce_ids)
        missing_products.delete()

        # Delete missing messages
        missing_salesforce_message_ids = existing_salesforce_message_ids - set(message_info['MessageId'] for message_info in message_data)
        missing_messages = Message.objects.filter(salesforce_id__in=missing_salesforce_message_ids)
        missing_messages.delete()

        # Save updated products
        for updated_product in updated_products:
            updated_product.save()

        # Save updated messages
        for updated_message in updated_messages:
            updated_message.save()

        # Save new products
        Product.objects.bulk_create(new_products)

        # Save new messages
        Message.objects.bulk_create(new_messages)


        message = 'OCE Uygulaması üzerinden yapılan ürün/mesaj değişiklikler güncellenmiştir.'
        Notification.objects.create(message = message)        

        return Response('Data saved/updated successfully.', status=200)


@login_required
def folders(request):
    user = request.user
    company = user.company  # Access the company object from the user
    folders = Folder.objects.filter(company=company).order_by('-created_date')
    context = {
        'folders': folders,
        'user' : user,
    }
    return render(request, 'folders.html', context)

@login_required
def folder_list(request):
    user = request.user
    company = user.company  # Access the company object from the user
    folders = Folder.objects.filter(company=company).order_by('-created_date')
    context = {
        'folders':folders,
        'user' : user,
    }
    return render(request, 'folder-list.html', context)

@login_required
def folder_details(request, id):
    user = request.user
    company = user.company
    presentations = Presentation.objects.filter(folder_id=id, company=company)
    pre_folder = Folder.objects.get(id=id)
    # Fetch related products for each presentation
    for presentation in presentations:
        presentation.products = Product.objects.filter(assets__presentation=presentation).distinct()
        presentation.remaining_products = presentation.products.count() - 2

    context = {
        'presentations' : presentations,
        'pre_folder' : pre_folder,
        'user' : user,
    }
    return render(request, 'folder-details.html', context)

@login_required
def presentation(request):
    user = request.user
    company = user.company
    presentations = Presentation.objects.filter(company=company).order_by('-created_date')
     # Fetch related products for each presentation
    for presentation in presentations:
        presentation.products = Product.objects.filter(assets__presentation=presentation).distinct()
        presentation.remaining_products = presentation.products.count() - 2
    context = {
        'presentations' : presentations,
        'user' : user,
    }
    return render(request, 'presentation.html', context)

@login_required
def presentation_list(request):
    user = request.user
    company = user.company
    presentations = Presentation.objects.filter(company=company).order_by('-created_date')
    context = {
        'presentations' : presentations,
        'user' : user,
    }
    return render(request, 'presentation-list.html', context)

@login_required
def edit(request,id):
    user = request.user
    company = user.company
    assets = Asset.objects.filter(presentation_id=id, company=company).order_by('sort_number')
    firstAsset = assets.first()
    pre = Presentation.objects.get(id=id, company=company)
    products = Product.objects.all()
    messages = Message.objects.all()
    context = {
        'assets' : assets,
        'pre' : pre,
        'firstAsset' : firstAsset,
        'products': products,
        'messages': messages,
        'user' : user,
    }
    return render(request, 'edit.html', context)


@login_required
def settings(request):
    user = request.user
    context = {
        'user': user,
    }
    return render(request, 'settings.html', context)



def createfolder(request):
    if request.method == 'POST':
        name = request.POST['newfilename']
        folder = Folder(name=name)
        folder.save(request=request)  # Pass the request object
    return redirect('folders')

def createfolderlist(request):
    if request.method=='POST':
        name = request.POST['newfilename']
        folder = Folder(name=name)
        folder.save(request=request)
        user = request.user
        company = user.company  # Access the company object from the user
        folders = Folder.objects.filter(company=company).order_by('-created_date')
        context = {
            'folders': folders,
            'user' : user,
        }
        return render(request, 'folders.html', context)

def createpresentation(request):
    if request.method=='POST':
        name = request.POST['newpresentationname']
        pre = Presentation(name=name)
        pre.save(request=request)  # Pass the request object
        user = request.user
        company = user.company  # Access the company object from the user
        presentations = Presentation.objects.filter(company=company).order_by('-created_date')
        for presentation in presentations:
            presentation.products = Product.objects.filter(assets__presentation=presentation).distinct()
            presentation.remaining_products = presentation.products.count() - 2
        context = {
            'presentations' : presentations,
            'openupload' : True,
            'pre' : pre,
            'user' : user,
        }
        return render(request, 'presentation.html', context)
    
def createpresentationfile(request, id):
    if request.method=='POST':
        user = request.user
        name = request.POST['newpresentationname']
        pre = Presentation(name=name)
        pre.folder_id = id
        pre.save(request=request)
        presentations = Presentation.objects.filter(folder_id=id).order_by('-created_date')
        for presentation in presentations:
            presentation.products = Product.objects.filter(assets__presentation=presentation).distinct()
            presentation.remaining_products = presentation.products.count() - 2
        pre_folder = Folder.objects.get(id=id)
        context = {
        'presentations' : presentations,
        'pre_folder' : pre_folder,
        'openupload' : True,
        'pre' : pre,
        'user' : user,
    }
        return render(request, 'folder-details.html', context)
    
def createpresentationlist(request):
    if request.method=='POST':
        name = request.POST['newpresentationname']
        pre = Presentation(name=name)
        pre.save(request=request)
    return redirect('presentation_list')

def renamefile(request,id):
    if request.method=='POST':
        name = request.POST['newfilename']
        folder =  Folder.objects.get(id=id)
        folder.name=name
        folder.save()
        return redirect('folders')

def presentation_settings(request,id):
    if request.method=='POST':
        if 'presentation-submit' in request.POST:
            name = request.POST['newpresentationname']
            start_date_str = request.POST['preStart']
            end_date_str = request.POST['preEnd']
            
            # Convert start and end dates to the desired format
            start_date = datetime.strptime(start_date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%d-%m-%Y').strftime('%Y-%m-%d')

            presentation =  Presentation.objects.get(id=id)
            presentation.name=name
            presentation.start_date=start_date
            presentation.end_date=end_date
            presentation.save()
            pre_folder = Folder.objects.get(id=presentation.folder_id)
            return redirect('presentation')
        if 'presentation-list-submit' in request.POST:
            name = request.POST['newpresentationname']
            start_date_str = request.POST['preStart']
            end_date_str = request.POST['preEnd']
            
            # Convert start and end dates to the desired format
            start_date = datetime.strptime(start_date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%d-%m-%Y').strftime('%Y-%m-%d')

            presentation =  Presentation.objects.get(id=id)
            presentation.name=name
            presentation.start_date=start_date
            presentation.end_date=end_date
            presentation.save()
            pre_folder = Folder.objects.get(id=presentation.folder_id)
            return redirect('presentation_list')
        if 'file-details-submit' in request.POST:
            name = request.POST['newpresentationname']
            start_date_str = request.POST['preStart']
            end_date_str = request.POST['preEnd']
            
            # Convert start and end dates to the desired format
            start_date = datetime.strptime(start_date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%d-%m-%Y').strftime('%Y-%m-%d')

            presentation =  Presentation.objects.get(id=id)
            presentation.name=name
            presentation.start_date=start_date
            presentation.end_date=end_date
            presentation.save()
            pre_folder = Folder.objects.get(id=presentation.folder_id)
            return redirect(folder_details,pre_folder.id)


def renamepresentationlist(request,id):
    if request.method=='POST':
        name = request.POST['newpresentationname']
        presentation =  Presentation.objects.get(id=id)
        presentation.name=name
        presentation.save()
        return redirect('presentation_list')
    
def renamefilelist(request,id):
    if request.method=='POST':
        name = request.POST['newfilename']
        folder =  Folder.objects.get(id=id)
        folder.name=name
        folder.save()
        return redirect('folder_list')


def deletefile(request,id):
    folder =  Folder.objects.get(id=id)
    folder.delete()
    return redirect('folders') 

def deletepresentation(request,id):
    presentation =  Presentation.objects.get(id=id)
    presentation.delete()
    return redirect('presentation')   

def deletepresentationdetail(request,id):
    presentation =  Presentation.objects.get(id=id)
    preid = presentation.folder_id
    presentation.delete()
    return redirect( 'folder_details', preid)   

def deletepresentationlist(request,id):
    presentation =  Presentation.objects.get(id=id)
    presentation.delete()
    return redirect('presentation_list')  

def deletefilelist(request,id):
    folder =  Folder.objects.get(id=id)
    folder.delete()
    return redirect('folder_list')

@csrf_exempt
def uploadimages(request, id):
    if request.method == 'POST':
        my_file = request.FILES.get('file')
        file_size = my_file.size

        # Convert file size to MB
        file_size_mb = file_size / (1024 * 1024)

        # Create the Asset object and save the original image
        asset = Asset(img=my_file, name=my_file.name, presentation_id=id, size = file_size_mb)
        asset.save(request=request)


        return HttpResponse({'success': 'success'})
    return HttpResponse({'false': 'false'})

@csrf_exempt
def uploadimagesfile(request, id):
    if request.method == 'POST':
        my_file = request.FILES.get('file')
        file_size = my_file.size

        # Convert file size to MB
        file_size_mb = file_size / (1024 * 1024)

        # Create the Asset object and save the original image
        asset = Asset(img=my_file, name=my_file.name, presentation_id=id, size = file_size_mb)
        asset.save(request=request)


        return HttpResponse({'success': 'success'})
    return HttpResponse({'false': 'false'})

@csrf_exempt
def uploadimagesedit(request, id):
    if request.method == 'POST':
        my_file = request.FILES.get('file')
        file_size = my_file.size

        # Convert file size to MB
        file_size_mb = file_size / (1024 * 1024)

        # Create the Asset object and save the original image
        asset = Asset(img=my_file, name=my_file.name, presentation_id=id, size = file_size_mb)
        asset.save(request=request)
        return HttpResponse({'success':'success'})
    return  HttpResponse({'false':'false'})

@csrf_exempt
def delete_asset(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    asset.delete()
    return JsonResponse({'status': 'success'})

def asset_sort(request):
    assets = json.loads(request.POST.get('sort'))
    for a in assets:
        asset = get_object_or_404(Asset, pk=int(a['pk']))
        asset.sort_number = a['order']
        asset.save()

    return HttpResponse('saved')

def get_asset_coordinates(request):
    asset_id = request.GET.get('asset_id')
    asset_coordinates = AssetCoordinate.objects.filter(asset_id=asset_id)
    asset_coord_list = []
    for coord in asset_coordinates:
        linked_asset_name = ''
        if coord.linked_asset:
            linked_asset = Asset.objects.filter(id=coord.linked_asset_id).first()
            linked_asset_name = linked_asset.name if linked_asset else ''
        asset_coord_list.append({
            'id' : coord.id,
            'coordinate_type': coord.coordinate_type,
            'start_top': coord.start_top,
            'start_left': coord.start_left,
            'end_top': coord.end_top,
            'end_left': coord.end_left,
            'is_embedded' : coord.is_embedded,
            'isEveryLink' : coord.isEveryLink,
            'linked_asset_id': coord.linked_asset_id,
            'linked_asset_name': linked_asset_name,
            'linked_url': coord.linked_url,
            'image': coord.image.url if coord.image else None,
            'video': coord.video.url if coord.video else None,
        })
    return JsonResponse(asset_coord_list, safe=False)

def save_sequence_info(request):
    seqinfo = json.loads(request.POST.get('seq'))
    asset = get_object_or_404(Asset, pk=(seqinfo['pk']))
    asset.name = seqinfo['name']
    """ if seqinfo['start']:
        input_start = datetime.strptime(seqinfo['start'], '%d-%m-%Y')
        asset.activation_date = input_start.strftime('%Y-%m-%d')
    else:
        asset.activation_date = None
    if seqinfo['end']:
        input_end = datetime.strptime(seqinfo['end'], '%d-%m-%Y')
        asset.deactivation_date = input_end.strftime('%Y-%m-%d')
    else:
        asset.deactivation_date = None """
    asset.save()

    return HttpResponse('saved')

def save_link(request):
    if request.method == 'POST':
        # Retrieve the data from the AJAX request
        isEveryLink = request.POST.get('isEveryLink')
        start_top = request.POST.get('start_top')
        start_left = request.POST.get('start_left')
        end_top = request.POST.get('end_top')
        end_left = request.POST.get('end_left')
        coordinate_type = request.POST.get('coordinate_type')
        asset_id = request.POST.get('asset_id')
        linked_asset_id = request.POST.get('linked_asset_id')

        if isEveryLink.lower() == "true":
            isEveryLink = True
            asset = get_object_or_404(Asset, id=asset_id)
            presentation_id = asset.presentation_id

            # Retrieve all child assets related to the presentation
            child_assets = Asset.objects.filter(presentation_id=presentation_id)

            # Create a list of AssetCoordinate objects
            asset_coordinates = []
            for child_asset in child_assets:
                asset_coordinate = AssetCoordinate(
                    asset_id=child_asset.id,
                    linked_asset_id=linked_asset_id,
                    coordinate_type=coordinate_type,
                    start_top=start_top,
                    start_left=start_left,
                    end_top=end_top,
                    end_left=end_left,
                    isEveryLink = isEveryLink
                )
                asset_coordinates.append(asset_coordinate)

            # Perform bulk save operation for all AssetCoordinate objects
            AssetCoordinate.objects.bulk_create(asset_coordinates)

            # Return a success response
            return JsonResponse({'status': 'success', 'message': 'Data saved to all assets in presentation successfully'})

        elif isEveryLink.lower() == "false":
            # Retrieve the linked asset object
            linked_asset = Asset.objects.get(id=linked_asset_id)

            # Create and save a new AssetCoordinate object
            asset_coordinate = AssetCoordinate(
                asset_id=asset_id,
                linked_asset_id=linked_asset.id,
                coordinate_type=coordinate_type,
                start_top=start_top,
                start_left=start_left,
                end_top=end_top,
                end_left=end_left,
            )
            asset_coordinate.save()

            # Return a success response
            return JsonResponse({'status': 'success', 'message': 'Data saved successfully'})
    else:
        # Return an error response
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def save_popup(request):
    if request.method == 'POST':
        # Get the form data from the POST request
        file = request.FILES.get('file')
        start_top = request.POST.get('start_top')
        start_left = request.POST.get('start_left')
        end_top = request.POST.get('end_top')
        end_left = request.POST.get('end_left')
        coordinate_type = request.POST.get('coordinate_type')
        asset_id = request.POST.get('asset_id')

        # Get the size of the uploaded file in MB
        file_size = file.size / (1024 * 1024)

        # Create the AssetCoordinate object
        asset_coordinate = AssetCoordinate(
            asset_id=asset_id,
            coordinate_type=coordinate_type,
            start_top=start_top,
            start_left=start_left,
            end_top=end_top,
            end_left=end_left,
            image=file,
            size = file_size
        )

        # Save the AssetCoordinate object
        asset_coordinate.save()

        # Return a JSON response indicating success
        return JsonResponse({'status': 'success', 'message': 'Asset Coordinate saved successfully'})
    else:
        # Return a JSON response indicating error
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def save_video(request):
    if request.method == 'POST':
        # Get the form data from the POST request
        file = request.FILES.get('file')
        isEmbedded = request.POST.get('isEmbedded')
        start_top = request.POST.get('start_top')
        start_left = request.POST.get('start_left')
        end_top = request.POST.get('end_top')
        end_left = request.POST.get('end_left')
        coordinate_type = request.POST.get('coordinate_type')
        asset_id = request.POST.get('asset_id')

        allowed_formats = ('.avi', '.wmv', '.mpg', '.mp4')
        if isEmbedded.lower() == "true":
            isEmbedded = True
        elif isEmbedded.lower() == "false":
            isEmbedded = False
        # Check if file format is supported
        if not file.name.endswith(allowed_formats):
            raise ValidationError('Only AVI, WMV, MPG, and MP4 video formats are supported.')

        if file.size >50 * 1024 * 1024:  # 50 MB in bytes
            raise ValidationError('Video file size should be limited to 50 MB.')
        
        # Check video duration is within limit of 2 minutes (120 seconds)
        video_duration = get_video_duration(file)  # Replace with actual code to get video duration
        if video_duration > 500:
            raise ValidationError('Video duration should be limited to 2 minutes.')

        # Get the size of the video in MB
        video_size = file.size / (1024 * 1024)

        # Create the AssetCoordinate object
        asset_coordinate = AssetCoordinate(
            asset_id=asset_id,
            coordinate_type=coordinate_type,
            start_top=start_top,
            start_left=start_left,
            end_top=end_top,
            end_left=end_left,
            video=file,  # Save the original file without converting
            is_embedded = isEmbedded,
            size = video_size
        )

        # Save the AssetCoordinate object
        asset_coordinate.save()

        # Return a JSON response indicating success
        return JsonResponse({'status': 'success', 'message': 'Asset Coordinate saved successfully'})
    else:
        # Return a JSON response indicating error
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def delete_accoord(request):
    if request.method == 'POST':
        asset_coord_id = request.POST.get('assetCoordId')
        # Perform deletion logic here based on the asset_coord_id
        ac = AssetCoordinate.objects.get(id=asset_coord_id)
        if ac.isEveryLink == True:
            # Retrieve all child assets related to the presentation
            AssetCoordinate.objects.filter(linked_asset=ac.linked_asset, isEveryLink = True).delete()


            # Return a success response
            return JsonResponse({'status': 'success', 'message': 'Data deleted from all assets in presentation successfully'})
        else:
            ac.delete()
            # Return JSON response indicating success
            return JsonResponse({'success': True})
    
    # If request method is not POST, return JSON response with error
    return JsonResponse({'error': 'Invalid request method'})

@csrf_exempt
def get_products_messages(request):
    asset_id = request.POST.get('assetId')
    try:
        # Retrieve the related products for the asset
        asset = Asset.objects.get(id=asset_id)
        products = asset.products.all()
        messages = asset.messages.values('id', 'name')  # Add the desired message fields here

        # Prepare the data to be sent back as JSON response
        data = {
            'products': [],
            'messages': list(messages),
        }

        for product in products:
            product_data = {
                'id': product.id,
                'name': product.name,
            }
            data['products'].append(product_data)

        return JsonResponse(data)

    except Asset.DoesNotExist:
        return JsonResponse({'error': 'Asset not found'}, status=404)

@csrf_exempt
def save_product_messages(request):
    if request.method == 'POST':
        asset_id = request.POST.get('assetId')
        product_ids = request.POST.getlist('products[]')
        message_ids = request.POST.getlist('messages[]')

        try:
            asset = Asset.objects.get(id=asset_id)
            existing_products = asset.products.all()
            existing_messages = asset.messages.all()

            # Remove existing product and message relations not included in the request
            for product in existing_products:
                if str(product.id) not in product_ids:
                    asset.products.remove(product)

            for message in existing_messages:
                if str(message.id) not in message_ids:
                    asset.messages.remove(message)

            # Add new product and message relations
            for product_id in product_ids:
                product = get_object_or_404(Product, id=product_id)
                asset.products.add(product)

            for message_id in message_ids:
                message = get_object_or_404(Message, id=message_id)
                asset.messages.add(message)

            return JsonResponse({'success': True})

        except Asset.DoesNotExist:
            return JsonResponse({'error': 'Asset not found'}, status=404)

    return JsonResponse({'error': 'Invalid request'}, status=400)



def download_folder(request):
    if request.method == 'POST':
        # Get the form data from the POST request
        pre_id = request.POST.get('preId')

        # Get the presentation object and related assets
        pre = Presentation.objects.get(id=pre_id)
        assets = Asset.objects.filter(presentation_id=pre_id).order_by('sort_number')

        # Create a temporary directory to store the zip files
        temp_dir = tempfile.mkdtemp()

        # Loop over each asset and create a new directory and zip file for each one
        for asset in assets:
            asset_name = asset.name.split(".")[0]
            asset_dir = os.path.join(temp_dir, asset_name)
            os.mkdir(asset_dir)

            # Copy the HTML, CSS, and JS files from the original directory
            shutil.copytree('Editor/renderedTemp/css', os.path.join(asset_dir, 'css'))
            shutil.copytree('Editor/renderedTemp/js', os.path.join(asset_dir, 'js'))
            shutil.copytree('Editor/renderedTemp/media', os.path.join(asset_dir, 'media'))
            shutil.copyfile('Editor/renderedTemp/01_index.html', os.path.join(asset_dir, '01_index.html'))
            shutil.copytree('Editor/renderedTemp/parameters', os.path.join(asset_dir, 'parameters'))

            # Render the HTML file with the asset's variables
            temp_xml = 'renderedTemp/parameters/parameters.xml'
            template = 'renderedTemp/01_index.html'
            asset_coordinates = AssetCoordinate.objects.filter(asset_id=asset.id)
            seqId = asset.name.split(".")[0]
            contextxml = {'seqId': seqId}
            context = {'asset': asset, 'asset_coordinates': asset_coordinates, 'seqId': seqId}
            for coordinate in asset_coordinates:
                if coordinate.linked_asset:
                    linked_asset_name = coordinate.linked_asset.name.split(".")[0]
                    coordinate.linked_asset_name = linked_asset_name
            render_xml = render_to_string(temp_xml, contextxml)
            rendered_html = render_to_string(template, context)

            # Save the rendered HTML to the new directory
            with open(os.path.join(asset_dir, 'parameters/parameters.xml'), 'w', encoding='utf-8') as f:
                f.write(render_xml)
            with open(os.path.join(asset_dir, '01_index.html'), 'w', encoding='utf-8') as f:
                f.write(rendered_html)

            # Copy any related images to the new directory's media folder
            shutil.copyfile(asset.img.path, os.path.join(asset_dir, asset.img.name))
            thumbnail_filename = os.path.join(asset_dir, "01_thumbnail" + os.path.splitext(asset.thumbnail.path)[1])
            shutil.copyfile(asset.thumbnail.path, thumbnail_filename)

            for ac in asset_coordinates:
                # Copy the image field to the destination directory
                if ac.image:
                    final_path = ac.image.name
                    shutil.copyfile(ac.image.path, os.path.join(asset_dir, f"media/{final_path}"))

                # Copy the video field to the destination directory
                if ac.video:
                    final_path = ac.video.name
                    shutil.copyfile(ac.video.path, os.path.join(asset_dir, f"media/{final_path}"))

            # Create a zip file for the current asset directory
            asset_zip_file = os.path.join(temp_dir, f"{asset_name}.zip")
            with zipfile.ZipFile(asset_zip_file, 'w') as zf:
                # Add the contents of the asset directory to the zip file
                for root, dirs, files in os.walk(asset_dir):
                    for file in files:
                        zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), asset_dir))

            # Clean up the asset directory after creating the zip file
            shutil.rmtree(asset_dir)

        # Create a new response object containing the zip files
        response = HttpResponse(content_type='application/zip')
        zip_filename = f"{pre.name.replace(' ', '_')}.zip"
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

        # Add the zip files to the response
        with zipfile.ZipFile(response, 'w') as final_zip:
            # Add each asset zip file to the final zip file
            for asset in assets:
                asset_zip_file = os.path.join(temp_dir, f"{asset.name.split('.')[0]}.zip")
                final_zip.write(asset_zip_file, os.path.basename(asset_zip_file))

        # Clean up the temporary directory after creating the final zip file
        shutil.rmtree(temp_dir)

        return response
from django.utils.html import escapejs
@login_required
def preview(request,id):
    user = request.user
    company = user.company  # Access the company object from the user
    pre_id = id
    pre = Presentation.objects.get(id=pre_id, company=company)
    # Get the presentation object and related assets
    assets = Asset.objects.filter(presentation_id=pre_id, company=company).order_by('sort_number')

    # Create a dictionary to hold asset coordinates grouped by asset
    asset_coordinates_dict = {}

    # Loop over each asset and fetch its related asset coordinates
    for asset in assets:
        asset_coordinates = AssetCoordinate.objects.filter(asset_id=asset.id)
        asset_coordinates_dict[asset.id] = list(asset_coordinates.values())

    # Convert the assets and asset_coordinates_dict to JSON
    assets_json = json.dumps(list(assets.values()))
    asset_coordinates_json = json.dumps(asset_coordinates_dict)

    # Escape the JSON strings for safe embedding in JavaScript
    assets_json_escaped = escapejs(assets_json)
    asset_coordinates_json_escaped = escapejs(asset_coordinates_json)

    # Return the URL of the first HTML file along with asset coordinates as a JSON response
    context = {
        'assets_json': assets_json_escaped,
        'asset_coordinates_json': asset_coordinates_json_escaped,
        'user':user,
        'pre' : pre
    }
    return render(request, 'preview.html', context)


@csrf_exempt
def download_images_as_pdf(request):
    presentation_id = request.GET.get('presentation_id', None)
    assets = Asset.objects.filter(presentation_id=presentation_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="images.pdf"'

    # Create a canvas and set the page size to letter
    
    c = canvas.Canvas(response, pagesize=(625, 384))

    # Loop through all the assets and add their images to the PDF
    for asset in assets:
        if asset.img:
            c.drawImage(asset.img.path, 0, 0, 625, 384)
            c.showPage()
        asset_coordinates = AssetCoordinate.objects.filter(asset__in=assets)
        # Loop through all the asset coordinates and add their images to the PDF
        for asset_coordinate in asset_coordinates:
            if asset_coordinate.image:
                c.drawImage(asset_coordinate.image.path, 0, 0, 625, 384)
                c.showPage()

    c.save()
    return response



def push_Oce(request):
    if request.method == 'POST':
        user = request.user
        company = user.company
        salesforce_username = company.salesforce_username
        salesforce_password = company.salesforce_password

        # Get the required data
        pre_id = request.POST.get('preId')
        presentation = Presentation.objects.get(id=pre_id)
        assets = Asset.objects.filter(presentation_id=pre_id).order_by('sort_number')

        # Create a temporary directory to store the zip files
        temp_dir = tempfile.mkdtemp()
        SEQUENCES_JSON = []

        # Loop over each asset and create a new directory and zip file for each one
        for asset in assets:
            asset_id = asset.id
            asset_name = asset.name.split(".")[0]
            asset_dir = os.path.join(temp_dir, asset_name)
            os.mkdir(asset_dir)

            # Copy the HTML, CSS, and JS files from the original directory
            shutil.copytree('Editor/renderedTemp/css', os.path.join(asset_dir, 'css'))
            shutil.copytree('Editor/renderedTemp/js', os.path.join(asset_dir, 'js'))
            shutil.copytree('Editor/renderedTemp/media', os.path.join(asset_dir, 'media'))
            shutil.copyfile('Editor/renderedTemp/01_index.html', os.path.join(asset_dir, '01_index.html'))
            shutil.copytree('Editor/renderedTemp/parameters', os.path.join(asset_dir, 'parameters'))

            # Render the HTML file with the asset's variables
            temp_xml = 'renderedTemp/parameters/parameters.xml'
            template = 'renderedTemp/01_index.html'
            asset_coordinates = AssetCoordinate.objects.filter(asset_id=asset_id)
            seqId = asset_id
            contextxml = {'seqId': seqId}
            context = {'asset': asset, 'asset_coordinates': asset_coordinates, 'seqId': seqId}
            for coordinate in asset_coordinates:
                if coordinate.linked_asset:
                    linked_asset_name = coordinate.linked_asset.name.split(".")[0]
                    coordinate.linked_asset_name = linked_asset_name
            render_xml = render_to_string(temp_xml, contextxml)
            rendered_html = render_to_string(template, context)

            # Save the rendered HTML to the new directory
            with open(os.path.join(asset_dir, 'parameters/parameters.xml'), 'w', encoding='utf-8') as f:
                f.write(render_xml)
            with open(os.path.join(asset_dir, '01_index.html'), 'w', encoding='utf-8') as f:
                f.write(rendered_html)

            # Copy any related images to the new directory's media folder
            shutil.copyfile(asset.img.path, os.path.join(asset_dir, asset.img.name))
            thumbnail_filename = os.path.join(asset_dir, "01_thumbnail" + os.path.splitext(asset.thumbnail.path)[1])
            shutil.copyfile(asset.thumbnail.path, thumbnail_filename)

            for ac in asset_coordinates:
                # Copy the image field to the destination directory
                if ac.image:
                    final_path = ac.image.name
                    shutil.copyfile(ac.image.path, os.path.join(asset_dir, f"media/{final_path}"))

                # Copy the video field to the destination directory
                if ac.video:
                    final_path = ac.video.name
                    shutil.copyfile(ac.video.path, os.path.join(asset_dir, f"media/{final_path}"))
            
            # Find all products related to the asset
            related_products = Product.objects.filter(assets__id=asset_id)


            # Create a dictionary to store the results
            products_messages = {}

            # Iterate over the related products and populate the dictionary
            for product in related_products:
                products_messages[product.salesforce_id] = []

                # Find messages related to the current product and asset
                related_messages = Message.objects.filter(product=product, assets__id=asset_id)
                
                # Add the Salesforce IDs of the related messages to the dictionary
                for message in related_messages:
                    products_messages[product.salesforce_id].append(message.salesforce_id)

            # Replace empty lists with null
            for key, value in products_messages.items():
                if not value:
                    products_messages[key] = None

            # Print the products_messages dictionary
            print(products_messages)
            # Create a zip file for the current asset directory
            asset_zip_file = os.path.join(temp_dir, f"{asset_name}.zip")
            with zipfile.ZipFile(asset_zip_file, 'w') as zf:
                # Add the contents of the asset directory to the zip file
                for root, dirs, files in os.walk(asset_dir):
                    for file in files:
                        zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), asset_dir))
            # Read the contents of the zipped file
            with open(os.path.join(temp_dir, asset_zip_file), 'rb') as f:
                contents = f.read()
            # Encode the contents to Base64
            base64_contents = base64.b64encode(contents).decode('utf-8')
            print(asset_zip_file.split(".")[0])
            # Create the base JSON structure
            json_data = {
                "name": asset_name.split(".")[0],
                "asset": False,
                "id": f'iqvia_tr_aut_{asset_id}',
                "file": base64_contents,
                "mandatory": True,

            }

            # Conditionally include the "products" field based on the content of the products_messages dictionary
            if products_messages:
                json_data["products"] = products_messages

            # Add the JSON data to the SEQUENCES_JSON list
            SEQUENCES_JSON.append(json_data)


            with zipfile.ZipFile(asset_zip_file, 'w') as zf:
                # Add the contents of the asset directory to the zip file
                for root, dirs, files in os.walk(asset_dir):
                    for file in files:
                        zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), asset_dir))

            # Clean up the asset directory after creating the zip file
            shutil.rmtree(asset_dir)
        

        # Make a POST request to insert the sequences
        if presentation.is_push_oce == True:
            url = r"http://ocesales-api-dev.solutions.iqvia.com/services/content/v2.0/clm/zip/update"
            headers = {"Content-Type": "application/json"}
            data = {
                "username" : salesforce_username,
                "password": salesforce_password,
                "is_sandbox": True,
                "presentation": {
                    "name":  presentation.name,
                    "id" : f'iqvia_tr_aut_{presentation.id}',
                    "double_tap_zoom": "Enabled",
                    "pinch_zoom": "Enabled",
                    "player_gesture": "TapBottom",
                    
                },
                "sequences": SEQUENCES_JSON,
                }
            if presentation.start_date:
                start_date_str = presentation.start_date.strftime('%Y-%m-%d')  # Convert date to string
                data["presentation"]["start_date"] = start_date_str

            if presentation.end_date:
                end_date_str = presentation.end_date.strftime('%Y-%m-%d')  # Convert date to string
                data["presentation"]["end_date"] = end_date_str
            
            response = requests.post(url, json=data ,headers=headers)
            try:
                print(response.json())
            except ValueError as e:
                print(response.content)
                print(str(e))
            # Handle the response from the API
            if response.status_code == 201:
                message = presentation.name + " sunumu OCE'de güncellenmiştir. Lütfen ilgili sunumu OCE üzerinden tekrar aktif etmeyi unutmayınız!"
                Notification.objects.create(user=user,message = message)
                data = response.json()
                print(data)
                return HttpResponse('Zip file processed successfully!')
            else:
                data = response.json()
                print(data)
                error_message = f"API returned status code {response.status_code}"
                ErrorLog.objects.create(level='ERROR', message=error_message)
                raise ValueError(error_message)


        if presentation.is_push_oce == False:
            url = r"https://ocesales-api-dev.solutions.iqvia.com/services/content/v2.0/clm/zip/insert"
            headers = {"Content-Type": "application/json"}
            data = {
                "username" : salesforce_username,
                "password": salesforce_password,
                "is_sandbox": True,
                "presentation": {
                    "name":  presentation.name,
                    "id" : f'iqvia_tr_aut_{presentation.id}',
                    "double_tap_zoom": "Enabled",
                    "pinch_zoom": "Enabled",
                    "player_gesture": "TapBottom",   
                },
                "sequences": SEQUENCES_JSON
                }
            
            if presentation.start_date:
                start_date_str = presentation.start_date.strftime('%Y-%m-%d')  # Convert date to string
                data["presentation"]["start_date"] = start_date_str

            if presentation.end_date:
                end_date_str = presentation.end_date.strftime('%Y-%m-%d')  # Convert date to string
                data["presentation"]["end_date"] = end_date_str

            response = requests.post(url, json=data ,headers=headers)
            print(response.json())
            # Handle the response from the API
            if response.status_code == 201:
                presentation.is_push_oce = True
                presentation.save()
                message = presentation.name + "sunumu OCE'ye gönderilmiştir. Lütfen ilgili sunumu OCE üzerinden aktif etmeyi ve bölge ataması yapmayı unutmayınız!"
                Notification.objects.create(user=user,message = message)
                data = response.json()
                print(data)
                return HttpResponse('Zip file processed successfully!')
            else:
                data = response.json()
                print(data)
                error_message = f"API returned status code {response.status_code}"
                ErrorLog.objects.create(level='ERROR', message=error_message)

                # Log the error and return an appropriate response
                raise ValueError(error_message)
        


def save_logo(request):
    if request.method == 'POST':
        logo = request.FILES.get('logo')
        user = request.user
        company = user.company  # Access the company object from the user
        company.logo=logo
        company.save()  # Save the updated company object
        message = "Şirket Logosu değiştirilmiştir."
        Notification.objects.create(message = message)
        logo_url = company.logo.url if company.logo else None
        return JsonResponse({'status': 'success', 'logo_url': logo_url})
    
    # If the request method is not POST, return an error response
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def update_username(request):
    if request.method == 'POST':
        new_username = request.POST.get('username')
        password = request.POST.get('password')

        user = request.user

        # Verify the password
        if not user.check_password(password):
            return JsonResponse({'success': False, 'message': 'Invalid password. Please try again.'})

        try:
            # Update the username
            user.username = new_username
            user.save()

            # Update the session authentication hash
            update_session_auth_hash(request, user)

            return JsonResponse({'success': True, 'message': 'Username updated successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')

        user = request.user

        # Verify the old password
        if not user.check_password(old_password):
            return JsonResponse({'success': False, 'message': 'Invalid old password.'})

        # Update the password
        user.set_password(new_password)
        user.save()

        # Update the session authentication hash
        update_session_auth_hash(request, user)

        return JsonResponse({'success': True, 'message': 'Password changed successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
def update_sf_username(request):
    if request.method == 'POST':
        new_username = request.POST.get('username')
        password = request.POST.get('password')

        user = request.user

        # Verify the password
        if not user.check_password(password):
            return JsonResponse({'success': False, 'message': 'Invalid password.'})

        # Update the Salesforce username
        user.company.salesforce_username = new_username
        user.company.save()

        return JsonResponse({'success': True, 'message': 'Salesforce username updated successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def change_sf_password(request):
    if request.method == 'POST':
        # Retrieve the submitted data
        new_password = request.POST.get('new_password')
        user_password = request.POST.get('user_password')
        user = request.user

        # Verify the password
        if not user.check_password(user_password):
            return JsonResponse({'success': False, 'message': 'Invalid User password.'})

        # Update the Salesforce username
        user.company.salesforce_password = new_password
        user.company.save()

        return JsonResponse({'success': True, 'message': 'Salesforce password updated successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})



@login_required
@csrf_exempt
def update_dark_mode(request):
    if request.method == "POST":
        dark_mode = request.POST.get("dark_mode")
        user = request.user
        if dark_mode == "true":
            dark_mode = True
        else:
            dark_mode = False
        try:
            user.dark_mode = dark_mode
            user.save()
            return JsonResponse({"status": "success"})
        except user.DoesNotExist:
            return JsonResponse({"status": "error", "message": "User not found"})
    
    return JsonResponse({"status": "error", "message": "Invalid request"})

@csrf_exempt
@login_required
def get_dark_mode_status(request):
    if request.method == "GET":
        user = request.user
        if user.is_authenticated:
            dark_mode = user.dark_mode
            return JsonResponse({"dark_mode": dark_mode})
        else:
            return JsonResponse({"error": "User not authenticated"})
    else:
        return JsonResponse({"error": "Invalid request"})


def get_notifications(request):
    user = request.user
    notifications = Notification.objects.filter(user=user).order_by('-created_at')[:15]

    data = {
        'notifications': [
            {
                'message': notification.message,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_read': notification.is_read
            }
            for notification in notifications
        ]
    }

    return JsonResponse(data)


@require_POST
@csrf_exempt
def mark_notifications_as_read(request):
    user = request.user
    Notification.objects.filter(user=user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})




##################################################################################################



def get_video_duration(file):
    if hasattr(file, 'temporary_file_path'):
        # If file is a TemporaryUploadedFile, get the temporary file's path
        file_path = file.temporary_file_path()
    else:
        # If file is not a TemporaryUploadedFile, read its contents from memory
        file_path = None
        with NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(file.read())
            file_path = tmp_file.name

    clip = VideoFileClip(file_path)
    duration = clip.duration
    clip.close()
    return duration


# Example usage: Get video frame rate
def get_video_frame_rate(file):
    cap = cv2.VideoCapture(file.path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps



