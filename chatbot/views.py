import json
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import connection
from .models import ChatMessage
import datetime


# ==================== TYPO TOLERANT DICTIONARY ====================

def clean_text(text):
    """Clean text: lowercase, remove extra whitespace, common typos"""
    text = text.lower().strip()
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text


def fix_typos(text):
    """Fix common typos in education-related terms"""
    # Common typos mapping
    typo_fixes = {
        'tearcher': 'teacher',
        'techer': 'teacher',
        'teachar': 'teacher',
        'techers': 'teachers',
        'techers': 'teachers',
        'teacheres': 'teachers',
        'tarcher': 'teacher',
        'tarchers': 'teachers',
        'staffs': 'staff',
        'staf': 'staff',
        'stduent': 'student',
        'stundent': 'student',
        'studnet': 'student',
        'studen': 'student',
        'students': 'students',
        'sutdents': 'students',
        'couese': 'course',
        'couse': 'course',
        'courses': 'courses',
        'subjet': 'subject',
        'subjetc': 'subject',
        'subjects': 'subjects',
        'attendace': 'attendance',
        'attenddance': 'attendance',
        'atendance': 'attendance',
        'result': 'results',
        'resutls': 'results',
        'marks': 'marks',
        'sesson': 'session',
        'sesion': 'session',
        'count': 'count',
        'counts': 'count',
        'nomber': 'number',
        'nuber': 'number',
    }
    
    words = text.split()
    fixed_words = []
    for word in words:
        # Check if word is in typos
        if word in typo_fixes:
            fixed_words.append(typo_fixes[word])
        else:
            fixed_words.append(word)
    
    return ' '.join(fixed_words)


# Dictionary with variations (lowercase keys)
SQL_DICTIONARY = {
    # Students variations
    'show all students': "SELECT * FROM student_management_app_students LIMIT 20",
    'show me all students': "SELECT * FROM student_management_app_students LIMIT 20",
    'list all students': "SELECT * FROM student_management_app_students LIMIT 20",
    'list students': "SELECT * FROM student_management_app_students LIMIT 20",
    'show students': "SELECT * FROM student_management_app_students LIMIT 20",
    'all students': "SELECT * FROM student_management_app_students LIMIT 20",
    'students': "SELECT * FROM student_management_app_students LIMIT 20",
    'get all students': "SELECT * FROM student_management_app_students LIMIT 20",
    'display all students': "SELECT * FROM student_management_app_students LIMIT 20",
    'get students': "SELECT * FROM student_management_app_students LIMIT 20",
    'fetch students': "SELECT * FROM student_management_app_students LIMIT 20",
    
    # Student counts
    'count of students': "SELECT COUNT(*) as total FROM student_management_app_students",
    'student count': "SELECT COUNT(*) as total FROM student_management_app_students",
    'total students': "SELECT COUNT(*) as total FROM student_management_app_students",
    'how many students': "SELECT COUNT(*) as total FROM student_management_app_students",
    'number of students': "SELECT COUNT(*) as total FROM student_management_app_students",
    'students count': "SELECT COUNT(*) as total FROM student_management_app_students",
    'count students': "SELECT COUNT(*) as total FROM student_management_app_students",
    
    # Teachers/Staff variations
    'show all teachers': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'show teachers': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'list teachers': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'all teachers': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'teachers': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'show teacher': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'list teacher': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'teacher': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'list all teacher': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'show all teacher': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    'faculty': "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id",
    
    # Staff counts
    'count of staff': "SELECT COUNT(*) as total FROM student_management_app_staffs",
    'staff count': "SELECT COUNT(*) as total FROM student_management_app_staffs",
    'total staff': "SELECT COUNT(*) as total FROM student_management_app_staffs",
    'how many staff': "SELECT COUNT(*) as total FROM student_management_app_staffs",
    'teacher count': "SELECT COUNT(*) as total FROM student_management_app_staffs",
    'how many teachers': "SELECT COUNT(*) as total FROM student_management_app_staffs",
    'number of teachers': "SELECT COUNT(*) as total FROM student_management_app_staffs",
    'count teachers': "SELECT COUNT(*) as total FROM student_management_app_staffs",
    
    # Courses
    'show all courses': "SELECT * FROM student_management_app_courses",
    'list courses': "SELECT * FROM student_management_app_courses",
    'show courses': "SELECT * FROM student_management_app_courses",
    'all courses': "SELECT * FROM student_management_app_courses",
    'courses': "SELECT * FROM student_management_app_courses",
    'list all courses': "SELECT * FROM student_management_app_courses",
    'display courses': "SELECT * FROM student_management_app_courses",
    'get courses': "SELECT * FROM student_management_app_courses",
    
    # Course counts
    'count of courses': "SELECT COUNT(*) as total FROM student_management_app_courses",
    'course count': "SELECT COUNT(*) as total FROM student_management_app_courses",
    'how many courses': "SELECT COUNT(*) as total FROM student_management_app_courses",
    'number of courses': "SELECT COUNT(*) as total FROM student_management_app_courses",
    
    # Subjects
    'show all subjects': "SELECT * FROM student_management_app_subjects LIMIT 20",
    'list subjects': "SELECT * FROM student_management_app_subjects LIMIT 20",
    'show subjects': "SELECT * FROM student_management_app_subjects LIMIT 20",
    'all subjects': "SELECT * FROM student_management_app_subjects LIMIT 20",
    'subjects': "SELECT * FROM student_management_app_subjects LIMIT 20",
    'list all subjects': "SELECT * FROM student_management_app_subjects LIMIT 20",
    
    # Subject counts
    'count of subjects': "SELECT COUNT(*) as total FROM student_management_app_subjects",
    'subject count': "SELECT COUNT(*) as total FROM student_management_app_subjects",
    'how many subjects': "SELECT COUNT(*) as total FROM student_management_app_subjects",
    'number of subjects': "SELECT COUNT(*) as total FROM student_management_app_subjects",
    
    # Attendance
    'show attendance': "SELECT * FROM student_management_app_attendance LIMIT 20",
    'attendance': "SELECT * FROM student_management_app_attendance LIMIT 20",
    'attendance report': "SELECT * FROM student_management_app_attendancereport LIMIT 20",
    'average attendance': "SELECT ROUND((SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as avg_attendance FROM student_management_app_attendancereport",
    'avg attendance': "SELECT ROUND((SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as avg_attendance FROM student_management_app_attendancoreport",
    'attendance percentage': "SELECT ROUND((SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as avg_attendance FROM student_management_app_attendancereport",
    
    # Results/Marks
    'show results': "SELECT * FROM student_management_app_studentresult LIMIT 20",
    'results': "SELECT * FROM student_management_app_studentresult LIMIT 20",
    'exam results': "SELECT * FROM student_management_app_studentresult LIMIT 20",
    'marks': "SELECT * FROM student_management_app_studentresult LIMIT 20",
    'show marks': "SELECT * FROM student_management_app_studentresult LIMIT 20",
    'average marks': "SELECT AVG(exam_mark) as avg_exam, AVG(assignment_mark) as avg_assignment FROM student_management_app_studentresult",
    
    # Dashboard
    'dashboard': "SELECT (SELECT COUNT(*) FROM student_management_app_students) as students, (SELECT COUNT(*) FROM student_management_app_courses) as courses, (SELECT COUNT(*) FROM student_management_app_staffs) as staff, (SELECT COUNT(*) FROM student_management_app_subjects) as subjects",
    'overview': "SELECT (SELECT COUNT(*) FROM student_management_app_students) as students, (SELECT COUNT(*) FROM student_management_app_courses) as courses, (SELECT COUNT(*) FROM student_management_app_staffs) as staff, (SELECT COUNT(*) FROM student_management_app_subjects) as subjects",
    'summary': "SELECT (SELECT COUNT(*) FROM student_management_app_students) as students, (SELECT COUNT(*) FROM student_management_app_courses) as courses, (SELECT COUNT(*) FROM student_management_app_staffs) as staff, (SELECT COUNT(*) FROM student_management_app_subjects) as subjects",
    
    # Help
    'help': "SELECT 'Try: show all students, list teachers, count students, show courses, average attendance' as suggestion",
    'what can i ask': "SELECT 'Try: show all students, list teachers, count students, show courses, average attendance' as suggestion",
}


# ==================== RULE-BASED SQL GENERATOR ====================

def generate_sql_from_rules(message):
    """Generate SQL based on rules when no dictionary match"""
    message = clean_text(message)
    message = fix_typos(message)
    
    # Detect table/entity
    entity = None
    if any(word in message for word in ['student', 'learner', 'stundent', 'stduent', 'studnet']):
        entity = 'student'
    elif any(word in message for word in ['teacher', 'tearcher', 'techer', 'staff', 'faculty', 'tarcher']):
        entity = 'teacher'
    elif any(word in message for word in ['course', 'couese', 'couse', 'program']):
        entity = 'course'
    elif any(word in message for word in ['subject', 'subjet', 'subjetc']):
        entity = 'subject'
    elif any(word in message for word in ['attendance', 'attendace', 'attenddance']):
        entity = 'attendance'
    elif any(word in message for word in ['result', 'mark', 'score', 'resutls']):
        entity = 'result'
    
    if not entity:
        return None
    
    # Detect action
    is_count = any(word in message for word in ['how many', 'count', 'total', 'number of', 'how much', 'counts'])
    is_list = any(word in message for word in ['show', 'list', 'get', 'display', 'fetch', 'view', 'give'])
    is_all = 'all' in message
    
    # Build SQL
    if entity == 'student':
        if is_count:
            sql = "SELECT COUNT(*) as total FROM student_management_app_students"
        elif is_list or is_all:
            sql = "SELECT * FROM student_management_app_students LIMIT 20"
        else:
            sql = "SELECT * FROM student_management_app_students LIMIT 20"
    
    elif entity == 'teacher':
        if is_count:
            sql = "SELECT COUNT(*) as total FROM student_management_app_staffs"
        elif is_list or is_all:
            sql = "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id"
        else:
            sql = "SELECT s.id, u.first_name, u.last_name, u.email FROM student_management_app_staffs s JOIN auth_user u ON s.admin_id_id = u.id"
    
    elif entity == 'course':
        if is_count:
            sql = "SELECT COUNT(*) as total FROM student_management_app_courses"
        else:
            sql = "SELECT * FROM student_management_app_courses"
    
    elif entity == 'subject':
        if is_count:
            sql = "SELECT COUNT(*) as total FROM student_management_app_subjects"
        else:
            sql = "SELECT * FROM student_management_app_subjects LIMIT 20"
    
    elif entity == 'attendance':
        if 'average' in message or 'avg' in message or 'percentage' in message:
            sql = "SELECT ROUND((SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as avg_attendance FROM student_management_app_attendancereport"
        elif is_count:
            sql = "SELECT COUNT(*) as total FROM student_management_app_attendancereport"
        else:
            sql = "SELECT * FROM student_management_app_attendance LIMIT 20"
    
    elif entity == 'result':
        if 'average' in message or 'avg' in message:
            sql = "SELECT AVG(exam_mark) as avg_exam, AVG(assignment_mark) as avg_assignment FROM student_management_app_studentresult"
        else:
            sql = "SELECT * FROM student_management_app_studentresult LIMIT 20"
    
    else:
        return None
    
    return sql


def find_matching_query(user_message):
    """Find matching SQL - try dictionary first, then rules"""
    # Clean the input
    original = user_message
    cleaned = clean_text(user_message)
    fixed = fix_typos(cleaned)
    
    # Try original
    if cleaned in SQL_DICTIONARY:
        return SQL_DICTIONARY[cleaned]
    
    # Try fixed typos
    if fixed in SQL_DICTIONARY:
        return SQL_DICTIONARY[fixed]
    
    # Try partial matches with cleaned text
    for key in SQL_DICTIONARY:
        if key in cleaned or cleaned in key:
            return SQL_DICTIONARY[key]
    
    # Try partial matches with fixed text
    for key in SQL_DICTIONARY:
        if key in fixed or fixed in key:
            return SQL_DICTIONARY[key]
    
    # Try rule-based generation
    sql = generate_sql_from_rules(user_message)
    if sql:
        return sql
    
    return "INVALID_QUERY"


def execute_sql_query(sql_query):
    """Execute SQL and return results"""
    if sql_query == "INVALID_QUERY":
        return {'success': False, 'error': 'INVALID_QUERY'}
    
    try:
        from decimal import Decimal
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            if not rows:
                return {
                    'success': True,
                    'columns': columns,
                    'data': [],
                    'row_count': 0
                }
            
            results = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    if isinstance(value, (datetime.datetime, datetime.date)):
                        value = value.isoformat()
                    elif isinstance(value, Decimal):
                        value = float(value)
                    row_dict[col] = value
                results.append(row_dict)
            
            return {
                'success': True,
                'columns': columns,
                'data': results,
                'row_count': len(results)
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def format_response(query_result):
    """Format query result for user"""
    if not query_result.get('success'):
        error = query_result.get('error', '')
        if error == 'INVALID_QUERY':
            return {
                'type': 'error',
                'message': 'Sorry, I could not understand your query. Try: "show all students", "list teachers", "count students", "show courses"'
            }
        return {
            'type': 'error',
            'message': 'Sorry, something went wrong. Please try a different query.'
        }
    
    data = query_result.get('data', [])
    row_count = query_result.get('row_count', 0)
    
    if row_count == 0:
        return {
            'type': 'text',
            'message': 'No data found for your query.'
        }
    
    # Single value result
    if row_count == 1 and len(query_result.get('columns', [])) == 1:
        value = data[0][query_result['columns'][0]]
        return {
            'type': 'stat',
            'message': f'Result: {value}',
            'value': value
        }
    
    # Table result
    return {
        'type': 'table',
        'message': f'Found {row_count} result(s)',
        'columns': query_result.get('columns', []),
        'data': data
    }


# ==================== DJANGO VIEWS ====================

@login_required
def chat_view(request):
    """Render chat interface"""
    chat_history = ChatMessage.objects.filter(user=request.user)[:50]
    context = {
        'chat_history': chat_history,
        'page_title': 'AI Chat Assistant'
    }
    return render(request, 'chatbot/chat.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def chat_api(request):
    """Process chat messages"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'response': {'type': 'error', 'message': 'Please enter a query'}
            })
        
        # Find and execute SQL
        sql_query = find_matching_query(user_message)
        query_result = execute_sql_query(sql_query)
        
        # Format response
        formatted_response = format_response(query_result)
        
        # Save to history
        ChatMessage.objects.create(
            user=request.user,
            message=user_message,
            response=formatted_response.get('message', ''),
            sql_query=sql_query if sql_query != 'INVALID_QUERY' else '',
            is_ai_response=True
        )
        
        return JsonResponse({
            'success': True,
            'response': formatted_response,
            'sql_query': sql_query
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'response': {'type': 'error', 'message': 'Invalid request format'}
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'response': {'type': 'error', 'message': 'Sorry, something went wrong. Please try again.'}
        })


@login_required
def get_chat_history(request):
    """Get chat history"""
    messages = ChatMessage.objects.filter(user=request.user)[:50]
    history = [{
        'message': m.message,
        'response': m.response,
        'timestamp': m.timestamp.isoformat(),
        'is_ai': m.is_ai_response
    } for m in messages]
    return JsonResponse({'success': True, 'history': history})


@login_required
def clear_chat(request):
    """Clear chat history"""
    ChatMessage.objects.filter(user=request.user).delete()
    return JsonResponse({'success': True, 'message': 'Chat history cleared'})


def test_chatbot(request):
    """Test endpoint"""
    return JsonResponse({
        'status': 'working',
        'total_queries': len(SQL_DICTIONARY),
        'message': 'Hybrid chatbot with typo tolerance'
    })
